"""Portable demo seed on a fresh database; repeat import must preserve later work."""
import json
from pathlib import Path
import shutil
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.application.account_service import AccountService
from app.application.demo_database import import_demo_database
from app.data.account_repository import AccountRepository
from app.data.product_repository import ProductRepository
from app.data.purchase_repository import PurchaseRepository
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def exported(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    return tmp_path


def test_full_import_and_application_roles_size_and_historical_orders(exported):
    result = import_demo_database(exported)
    assert result["applied"]
    assert (result["products"], result["historical_orders"], result["inventory_rows"], result["size_variants"]) == (181, 30, 183, 2)
    accounts = AccountRepository(exported / "runtime/commerce/accounts.sqlite3")
    service = AccountService(accounts)
    password = "Transfer demo passphrase 2026"
    service.register("buyer@example.test", "Demo buyer", password, "transfer-test", customer_id="C001")
    service.register("admin@example.test", "Demo admin", password, "transfer-test", role="admin")
    with TestClient(create_app(Settings(root=exported, load_models=False))) as api:
        assert api.get('/api/v1/catalog').json()["total"] == 181
        assert api.get('/api/v1/products/P181').status_code == 200
        assert api.get('/api/v1/media/products/P181').status_code == 200
        shirt = api.get('/api/v1/products/P041').json()["product"]
        assert {v["size"]: v["stock_quantity"] for v in shirt["variants"]} == {"M": 3, "L": 2}
        assert api.post('/api/v1/auth/login', headers={"X-Cortis-Intent": "account"}, json={"email": "buyer@example.test", "password": password}).status_code == 200
        assert api.get('/api/v1/orders/O001').status_code == 200
        assert api.get('/api/v1/orders/O002').status_code == 404
        assert api.get('/api/v1/admin/inventory').status_code == 403
        api.post('/api/v1/auth/logout', headers={"X-Cortis-Intent": "account"}, json={})
        assert api.post('/api/v1/auth/login', headers={"X-Cortis-Intent": "account"}, json={"email": "admin@example.test", "password": password}).status_code == 200
        assert api.get('/api/v1/admin/inventory?q=P041').status_code == 200


def test_repeated_import_never_resets_edited_stock(exported):
    initial = import_demo_database(exported)
    db_path = exported / "runtime/commerce/accounts.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE inventory SET quantity=1 WHERE product_id='P041-M'")
    again = import_demo_database(exported)
    assert not again["applied"] and initial["snapshot_id"] == again["snapshot_id"]
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT quantity FROM inventory WHERE product_id='P041-M'").fetchone()[0] == 1


def test_used_database_is_not_replaced(exported):
    accounts = AccountRepository(exported / "runtime/commerce/accounts.sqlite3")
    PurchaseRepository(accounts, ProductRepository(exported).products)
    with accounts.connection() as db:
        db.execute("UPDATE inventory SET quantity=1 WHERE product_id='P001'")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        import_demo_database(exported)
    with accounts.connection() as db:
        assert db.execute("SELECT quantity FROM inventory WHERE product_id='P001'").fetchone()[0] == 1


@pytest.mark.parametrize("change", ["quantity", "fingerprint"])
def test_bad_snapshot_does_not_create_database(exported, change):
    file = exported / "data/demo_database.json"
    seed = json.loads(file.read_text(encoding="utf-8"))
    if change == "quantity":
        seed["inventory"][0]["quantity"] = True
    else:
        seed["catalog_fingerprint"] = "0" * 64
    file.write_text(json.dumps(seed), encoding="utf-8")
    with pytest.raises(ValueError):
        import_demo_database(exported)
    assert not (exported / "runtime/commerce/accounts.sqlite3").exists()
