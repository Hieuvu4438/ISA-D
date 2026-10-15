"""Variant lifecycle against real SQLite/FastAPI; no encoder or speech calls."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.domain import AppError
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
ADMIN = {"X-Cortis-Intent": "admin"}
SHOP = {"X-Cortis-Intent": "commerce"}
AUTH = {"X-Cortis-Intent": "account"}
ADDRESS = {"recipient": "Buyer demo", "phone": "0900000000", "address_line": "Test address", "city": "Test city"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "variants.sqlite3"))) as client:
        response = client.post("/api/v1/auth/register", headers=AUTH, json={"email": "variants@example.test", "password": "test variant passphrase 2026", "display_name": "Variant buyer"})
        client.actor = response.json()["user"]["user_id"]
        with client.app.state.accounts.repository.connection() as db:
            db.execute("UPDATE accounts SET role='admin' WHERE user_id=?", (client.actor,))
        yield client


def allocate(api, size="40", quantity=2, pid="P001", **extra):
    revision = api.app.state.purchases.repository.snapshot()[1]
    return api.post(f"/api/v1/admin/products/{pid}/variants", headers=ADMIN,
                    json={"size": size, "quantity": quantity, "revision": revision, "reason": "Demo stock allocation", **extra})


def add(api, size=None, quantity=1, pid="P001"):
    cart = api.get("/api/v1/cart").json()["cart"]
    return api.post("/api/v1/cart/items", headers=SHOP, json={"product_id": pid, "quantity": quantity, "version": cart["version"], **({"variant_id": f"{pid}-{size}"} if size else {})})


def checkout(api):
    q = api.post("/api/v1/checkout/quote", headers=SHOP, json={})
    assert q.status_code == 200, q.text
    response = api.post("/api/v1/purchases", headers=SHOP, json={"quote_id": q.json()["quote"]["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": ADDRESS})
    assert response.status_code == 201, response.text
    return response.json()["order"]


def raw_stock(api):
    with api.app.state.accounts.repository.connection() as db:
        return dict(db.execute("SELECT product_id,quantity FROM inventory"))


def test_allocation_conserves_stock_and_retires_unsized_shopping(api):
    before = raw_stock(api)["P001"]
    assert add(api).status_code == 200
    old_quote = api.post("/api/v1/checkout/quote", headers=SHOP, json={}).json()["quote"]
    assert allocate(api).status_code == 201
    stock = raw_stock(api)
    assert stock["P001"] + stock["P001-40"] == before
    product = api.get("/api/v1/products/P001").json()["product"]
    assert product["stock_quantity"] == 2 and product["variants"][0]["size"] == "40"
    assert api.get("/api/v1/cart").json()["cart"]["items"][0]["issue"] == "VARIANT_REQUIRED"
    assert add(api).json()["error"]["code"] == "VARIANT_REQUIRED"
    assert api.post("/api/v1/checkout/quote", headers=SHOP, json={}).status_code == 409
    assert api.post("/api/v1/purchases", headers=SHOP, json={"quote_id": old_quote["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": ADDRESS}).status_code == 409
    # Removing the old unsized row still works, without choosing an arbitrary size.
    assert add(api, quantity=0).json()["cart"]["items"] == []
    assert add(api, "40", 2).status_code == 200
    assert add(api, "40", 3).json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert add(api, "41").json()["error"]["code"] == "VARIANT_UNAVAILABLE"
    assert api.get("/api/v1/catalog?q=P001&in_stock=true").json()["total"] == 1


def test_two_sizes_cart_order_snapshot_cancellation_and_legacy_order(api):
    assert add(api).status_code == 200
    legacy = checkout(api)
    assert allocate(api, "40", 2).status_code == 201
    assert allocate(api, "41", 3).status_code == 201
    assert add(api, "40", 2).status_code == add(api, "41", 1).status_code == 200
    rows = api.get("/api/v1/cart").json()["cart"]["items"]
    assert len(rows) == 2 and {row["variant_id"] for row in rows} == {"P001-40", "P001-41"}
    order = checkout(api)
    assert {line["size"] for line in order["items"]} == {"40", "41"}
    assert all(line["product_id"] == "P001" for line in order["items"])
    assert raw_stock(api)["P001-40"] == 0 and raw_stock(api)["P001-41"] == 2
    for _ in range(2):
        response = api.post(f"/api/v1/purchases/{order['order_id']}/cancel", headers=SHOP, json={"version": 0})
        assert response.status_code == 200
    assert raw_stock(api)["P001-40"] == 2 and raw_stock(api)["P001-41"] == 3
    # Pre-migration order returns to the original unallocated bucket, not a random size.
    before = raw_stock(api)["P001"]
    assert api.post(f"/api/v1/purchases/{legacy['order_id']}/cancel", headers=SHOP, json={"version": 0}).status_code == 200
    assert raw_stock(api)["P001"] == before + 1
    assert api.get("/api/v1/products/P001").json()["product"]["stock_quantity"] == 5


def test_size_specific_returns_receipt_and_limits(api):
    allocate(api, "40", 3)
    allocate(api, "41", 3)
    add(api, "40", 2)
    add(api, "41", 1)
    order = checkout(api)
    for status, version in [("shipped", 0), ("delivered", 1)]:
        assert api.post(f"/api/v1/admin/purchases/{order['order_id']}/status", headers=ADMIN, json={"status": status, "version": version, "reason": "Test delivery"}).status_code == 200
    endpoint = f"/api/v1/purchases/{order['order_id']}/returns"
    body = {"version": 2, "idempotency_key": str(uuid4()), "reason": "Wrong demo size", "items": [{"product_id": "P001", "variant_id": "P001-40", "quantity": 1}, {"product_id": "P001", "variant_id": "P001-41", "quantity": 1}]}
    result = api.post(endpoint, headers=SHOP, json=body)
    assert result.status_code == 201, result.text
    case = result.json()["return"]
    assert len(case["items"]) == 2 and {i["size"] for i in case["items"]} == {"40", "41"}
    assert api.post(endpoint, headers=SHOP, json=body).json()["replayed"] is True
    remaining = {i["variant_id"]: i["remaining_quantity"] for i in api.get(endpoint).json()["eligibility"]["items"]}
    assert remaining == {"P001-40": 1, "P001-41": 0}
    target = f"/api/v1/admin/returns/{case['return_id']}/status"
    assert api.post(target, headers=ADMIN, json={"status": "approved", "version": 0, "reason": "Approve test"}).status_code == 200
    receipt = [{"product_id": "P001", "variant_id": "P001-40", "restock_quantity": 1}, {"product_id": "P001", "variant_id": "P001-41", "restock_quantity": 0}]
    before = raw_stock(api)
    for _ in range(2):
        response = api.post(target, headers=ADMIN, json={"status": "received", "version": 1, "reason": "Inspect test", "receipt": receipt})
        assert response.status_code == 200, response.text
    after = raw_stock(api)
    assert after["P001-40"] == before["P001-40"] + 1
    assert after["P001-41"] == before["P001-41"] and after["P001"] == before["P001"]
    invalid = {**body, "idempotency_key": str(uuid4()), "items": [{"product_id": "P001", "variant_id": "P001-41", "quantity": 1}]}
    assert api.post(endpoint, headers=SHOP, json=invalid).json()["error"]["code"] == "RETURN_QUANTITY_CHANGED"


def test_allocation_atomic_audit_failure_stale_duplicates_and_restart(api):
    before = raw_stock(api)
    with api.app.state.accounts.repository.connection() as db:
        db.execute("CREATE TRIGGER fail_variant BEFORE INSERT ON admin_audit WHEN NEW.action='variant.allocate' BEGIN SELECT RAISE(ABORT,'test failure'); END")
    assert allocate(api).status_code == 500
    assert raw_stock(api) == before
    with api.app.state.accounts.repository.connection() as db:
        db.execute("DROP TRIGGER fail_variant")
    revision = api.app.state.purchases.repository.snapshot()[1]
    assert allocate(api).status_code == 201
    assert allocate(api).json()["error"]["code"] == "VARIANT_EXISTS"
    assert allocate(api, "41", revision=revision).json()["error"]["code"] == "INVENTORY_CHANGED"
    assert allocate(api, "41", quantity=999).json()["error"]["code"] == "INSUFFICIENT_STOCK"
    after = raw_stock(api)
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=api.app.state.accounts.repository.path))) as fresh:
        assert raw_stock(fresh) == after
        assert fresh.get("/api/v1/products/P001").json()["product"]["variants"][0]["stock_quantity"] == 2


def test_concurrent_allocation_and_variant_checkout_no_oversell(api):
    repository = api.app.state.admin.repository
    revision = api.app.state.purchases.repository.snapshot()[1]
    def create(size):
        try:
            repository.allocate_variant(api.actor, "P001", size, 1, revision, "Concurrent allocation")
            return True
        except AppError as error:
            assert error.code == "INVENTORY_CHANGED"
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(create, ["40", "41"])) == 1
    sku = api.get("/api/v1/products/P001").json()["product"]["variants"][0]["variant_id"]
    add(api, sku.split("-")[1])
    first_quote = api.app.state.purchases.quote(api.actor)
    other = api.post("/api/v1/auth/register", headers=AUTH, json={"email": "other-variant@example.test", "password": "other variant passphrase 2026", "display_name": "Other"}).json()["user"]["user_id"]
    add(api, sku.split("-")[1])
    other_quote = api.app.state.purchases.quote(other)
    def place(pair):
        user, quote = pair
        try:
            api.app.state.purchases.place(user, quote["quote_id"], str(uuid4()), ADDRESS)
            return True
        except AppError as error:
            assert error.code == "INSUFFICIENT_STOCK"
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(place, [(api.actor, first_quote), (other, other_quote)])) == 1
    assert raw_stock(api)[sku] == 0
    assert api.get("/api/v1/products/P001").json()["product"]["in_stock"] is False
    assert api.get("/api/v1/catalog?q=P001&in_stock=true").json()["total"] == 0


@pytest.mark.parametrize("size,pid,expected", [("M", "P001", 422), ("40", "P041", 422), ("m", "P041", 422), ("M", "P999", 404), ("M", "P041", 201)])
def test_size_category_validation(api, size, pid, expected):
    assert allocate(api, size, quantity=0, pid=pid).status_code == expected


def test_stock_mutation_and_auth_epoch_guard(api):
    allocate(api)
    before = raw_stock(api)
    account = api.app.state.accounts.repository
    with account.connection() as db:
        account.invalidate_sessions(db, api.actor)
    with pytest.raises(AppError):
        api.app.state.admin.repository.allocate_variant(api.actor, "P001", "41", 1, api.app.state.purchases.repository.snapshot()[1], "Old identity", expected_epoch=0)
    assert raw_stock(api) == before
    assert allocate(api, "41").status_code == 401


def test_size_facets_stock_intersection_and_strict_query(api):
    assert allocate(api, "M", 2, pid="P041").status_code == 201
    assert allocate(api, "L", 0, pid="P041").status_code == 201
    page = api.get("/api/v1/catalog?category=t_shirt&size=M&in_stock=true&limit=1").json()
    assert page["total"] == 1 and page["products"][0]["product_id"] == "P041"
    assert page["products"][0]["sizes"] == ["M", "L"]
    assert page["products"][0]["available_sizes"] == ["M"]
    assert {v["value"]: v["count"] for v in page["facets"]["size"]} == {"L": 0, "M": 1}
    assert api.get("/api/v1/catalog?size=L").json()["total"] == 1
    assert api.get("/api/v1/catalog?size=L&in_stock=true").json()["total"] == 0
    assert api.get("/api/v1/catalog?size=M&category=watch").json()["total"] == 0
    for query in ["size=m", "size=49", "size=", "size=M&size=L"]:
        assert api.get("/api/v1/catalog?" + query).status_code == 422
    payload = {"product_id": "P002", "variant_id": "P041-M", "quantity": 1, "version": 0}
    assert api.post("/api/v1/cart/items", headers=SHOP, json=payload).status_code == 422


def test_variant_order_partial_failure_rolls_back_both_sizes(api):
    allocate(api, "40", 2)
    allocate(api, "41", 2)
    add(api, "40")
    add(api, "41")
    quote = api.post("/api/v1/checkout/quote", headers=SHOP, json={}).json()["quote"]
    with api.app.state.accounts.repository.connection() as db:
        db.execute("UPDATE inventory SET quantity=0 WHERE product_id='P001-41'")
    before = raw_stock(api)
    response = api.post("/api/v1/purchases", headers=SHOP, json={"quote_id": quote["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": ADDRESS})
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert raw_stock(api) == before
    assert len(api.get("/api/v1/cart").json()["cart"]["items"]) == 2


def test_regular_user_cannot_allocate_or_write_variant_inventory(api):
    with api.app.state.accounts.repository.connection() as db:
        db.execute("UPDATE accounts SET role='user' WHERE user_id=?", (api.actor,))
    before = raw_stock(api)
    assert allocate(api).status_code == 403
    assert api.post("/api/v1/admin/inventory/P001-40", headers=ADMIN, json={"quantity": 1, "revision": 0, "reason": "No permissions"}).status_code == 403
    assert raw_stock(api) == before
