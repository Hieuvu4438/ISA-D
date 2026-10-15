"""Sale state against real SQLite/API, with explicit doubles only for ranking."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import numpy as np
import pytest

from app.application.query_service import Query
from app.application.search_service import SearchService
from app.domain import AppError, SearchOptions
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
ADMIN = {"X-Cortis-Intent": "admin"}
SHOP = {"X-Cortis-Intent": "commerce"}
ADDRESS = {"recipient": "Buyer demo", "phone": "0900000000", "address_line": "Test address", "city": "Test city"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "availability.sqlite3"))) as client:
        result = client.post("/api/v1/auth/register", headers={"X-Cortis-Intent": "account"}, json={"email": "availability@example.test", "password": "test availability passphrase 2026", "display_name": "Availability operator"})
        assert result.status_code == 201
        client.actor = result.json()["user"]["user_id"]
        with client.app.state.accounts.repository.connection() as db:
            db.execute("UPDATE accounts SET role='admin' WHERE user_id=?", (client.actor,))
        yield client


def change(api, state="archived", pid="P001", **extra):
    revision = api.app.state.purchases.repository.snapshot()[1]
    return api.post(f"/api/v1/admin/products/{pid}/sale-state", headers=ADMIN, json={"sale_state": state, "revision": revision, "reason": "Review catalog availability", **extra})


def add(api, pid="P001", sku=None, quantity=1):
    version = api.get("/api/v1/cart").json()["cart"]["version"]
    return api.post("/api/v1/cart/items", headers=SHOP, json={"product_id": pid, "quantity": quantity, "version": version, **({"variant_id": sku} if sku else {})})


def quote_body(api):
    quote = api.post("/api/v1/checkout/quote", headers=SHOP, json={})
    assert quote.status_code == 200
    return {"quote_id": quote.json()["quote"]["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": ADDRESS}


def test_hide_restore_public_lists_facets_detail_and_real_stock(api):
    before = api.get("/api/v1/products/P001").json()["product"]
    count = api.get("/api/v1/products?limit=1").json()["total"]
    assert change(api).status_code == 200
    detail = api.get("/api/v1/products/P001").json()["product"]
    assert detail["sale_state"] == "archived" and detail["stock_quantity"] == 0 and not detail["in_stock"]
    assert all(v["stock_quantity"] == 0 and not v["in_stock"] for v in detail["variants"])
    assert api.get("/api/v1/products?limit=1").json()["total"] == count - 1
    assert api.get("/api/v1/catalog?q=P001").json()["total"] == 0
    assert api.get("/api/v1/suggestions?q=P001").json()["products"] == []
    catalog = api.get("/api/v1/catalog?limit=100").json()
    assert sum(row["count"] for row in catalog["facets"]["category"]) == count - 1
    raw = api.get("/api/v1/admin/inventory?q=P001").json()["items"][0]
    assert raw["quantity"] == before["stock_quantity"] and raw["sale_state"] == "archived"
    assert api.get("/api/v1/admin/products?status=archived").json()["items"][0]["product_id"] == "P001"
    assert api.get("/api/v1/media/products/P001").status_code == 200
    assert change(api, "active").status_code == 200
    after = api.get("/api/v1/products/P001").json()["product"]
    assert after == before
    assert api.get("/api/v1/products?limit=1").json()["total"] == count


def test_saved_cart_wishlist_recovery_and_remove_while_archived(api):
    assert add(api).status_code == 200
    assert api.post("/api/v1/wishlist/items", headers=SHOP, json={"product_id": "P001", "saved": True}).status_code == 200
    assert change(api).status_code == 200
    cart = api.get("/api/v1/cart").json()["cart"]
    assert cart["has_issues"] and cart["items"][0]["issue"] == "PRODUCT_ARCHIVED"
    assert cart["items"][0]["available_quantity"] == 0
    wish = api.get("/api/v1/wishlist").json()["items"][0]
    assert wish["product"]["sale_state"] == "archived" and not wish["product"]["in_stock"]
    assert add(api).json()["error"]["code"] == "PRODUCT_ARCHIVED"
    assert api.post("/api/v1/checkout/quote", headers=SHOP, json={}).json()["error"]["code"] == "PRODUCT_ARCHIVED"
    assert add(api, quantity=0).status_code == 200
    assert api.get("/api/v1/cart").json()["cart"]["items"] == []
    assert change(api, "active").status_code == 200
    assert add(api).status_code == 200


def test_quote_before_archive_cannot_purchase_history_replay_and_cancel_survive(api):
    initial = api.get("/api/v1/products/P001").json()["product"]["stock_quantity"]
    assert add(api).status_code == 200
    body = quote_body(api)
    assert change(api).status_code == 200
    failed = api.post("/api/v1/purchases", headers=SHOP, json=body)
    assert failed.status_code == 409 and failed.json()["error"]["code"] == "PRODUCT_ARCHIVED"
    assert change(api, "active").status_code == 200
    placed = api.post("/api/v1/purchases", headers=SHOP, json=body)
    assert placed.status_code == 201
    order = placed.json()["order"]
    assert change(api).status_code == 200
    assert api.get(f"/api/v1/purchases/{order['order_id']}").json()["order"] == order
    replay = api.post("/api/v1/purchases", headers=SHOP, json=body)
    assert replay.status_code == 201 and replay.json()["replayed"] and replay.json()["order"] == order
    cancel = api.post(f"/api/v1/purchases/{order['order_id']}/cancel", headers=SHOP, json={"version": order["version"]})
    assert cancel.status_code == 200
    assert change(api, "active").status_code == 200
    assert api.get("/api/v1/products/P001").json()["product"]["stock_quantity"] == initial


def test_parent_archive_blocks_every_size_and_preserves_allocated_stock(api):
    revision = api.app.state.purchases.repository.snapshot()[1]
    allocated = api.post("/api/v1/admin/products/P001/variants", headers=ADMIN, json={"size": "40", "quantity": 2, "revision": revision, "reason": "Allocate demo sizes"})
    assert allocated.status_code == 201
    assert add(api, sku="P001-40").status_code == 200
    body = quote_body(api)
    assert change(api).status_code == 200
    assert not api.get("/api/v1/products/P001").json()["product"]["available_sizes"]
    assert api.post("/api/v1/purchases", headers=SHOP, json=body).json()["error"]["code"] == "PRODUCT_ARCHIVED"
    assert add(api, sku="P001-40").json()["error"]["code"] == "PRODUCT_ARCHIVED"
    assert change(api, "active").status_code == 200
    assert api.get("/api/v1/products/P001").json()["product"]["variants"][0]["stock_quantity"] == 2


def test_stale_revision_noop_audit_and_reopen(api):
    result = change(api).json()["availability"]
    again = change(api).json()["availability"]
    assert again == result
    assert change(api, "active", revision=0).status_code == 409
    audit = api.get("/api/v1/admin/audit").json()["events"]
    entries = [row for row in audit if row["action"] == "product.sale_state"]
    assert len(entries) == 1
    settings = api.app.state.services.settings
    with TestClient(create_app(settings)) as fresh:
        assert fresh.get("/api/v1/products/P001").json()["product"]["sale_state"] == "archived"
        assert fresh.get("/api/v1/catalog?q=P001").json()["total"] == 0


def test_audit_failure_rolls_back_state_and_revision(api, monkeypatch):
    repo = api.app.state.admin.repository
    def fail(*args):
        raise RuntimeError("audit unavailable")
    monkeypatch.setattr(repo, "audit", fail)
    with pytest.raises(RuntimeError):
        repo.sale_state(api.actor, "P001", "archived", 0, "Rollback test")
    assert api.get("/api/v1/products/P001").json()["product"]["sale_state"] == "active"
    assert api.app.state.purchases.repository.snapshot()[1] == 0


def test_archive_after_cart_precheck_is_rechecked_inside_transaction(api, monkeypatch):
    service = api.app.state.shopping
    original = service.repository.set_quantity
    def archive_then_write(*args, **kwargs):
        api.app.state.admin.repository.sale_state(api.actor, "P001", "archived", 0, "Concurrent archive")
        return original(*args, **kwargs)
    monkeypatch.setattr(service.repository, "set_quantity", archive_then_write)
    assert add(api).json()["error"]["code"] == "PRODUCT_ARCHIVED"
    assert api.get("/api/v1/cart").json()["cart"]["items"] == []


def test_admin_epoch_rechecked_and_competing_stock_update_serializes(api):
    repo = api.app.state.admin.repository
    def run(operation):
        try:
            if operation == "archive":
                return repo.sale_state(api.actor, "P001", "archived", 0, "Competing archive")["revision"]
            return repo.stock(api.actor, "P001", 100, 0, "Competing stock")["revision"]
        except AppError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, ["archive", "stock"]))
    assert sorted(map(str, results)) == ["1", "INVENTORY_CHANGED"]
    accounts = api.app.state.accounts.repository
    with accounts.connection() as db:
        accounts.invalidate_sessions(db, api.actor)
    with pytest.raises(AppError):
        repo.sale_state(api.actor, "P001", "active", 1, "Revoked operator", expected_epoch=0)
    assert api.app.state.purchases.repository.snapshot()[1] == 1


@pytest.mark.parametrize("mode", ["text", "voice", "image", "multimodal"])
def test_archived_high_score_never_reappears_in_ai_results(api, tmp_path, mode):
    repository = api.app.state.services.products
    rows = repository.products[:2]
    index = SimpleNamespace(available=True, fingerprint="a" * 64, product_vectors=np.tile(np.eye(1, 512, dtype=np.float32), (2, 1)),
                            retrieve=lambda _: [{"row": i, "product_id": p["product_id"], "score": .99 - .1 * i} for i, p in enumerate(rows)])
    service = SearchService(repository, SimpleNamespace(available=True, model_fingerprint="b" * 64), index, tmp_path)
    service.inventory = api.app.state.purchases.repository
    assert change(api).status_code == 200
    query = Query(mode, np.eye(1, 512)[0], None, None, SearchOptions(top_k=1), {} if mode == "image" else {"text": "giày"})
    result = service.search(query)
    assert [r["product"]["product_id"] for r in result["results"]] == ["P002"]


def test_admin_only_strict_state_reason_revision_and_published_parent(api):
    path = "/api/v1/admin/products/P001/sale-state"
    body = {"sale_state": "archived", "revision": 0, "reason": "Review product"}
    assert api.post(path, json=body).status_code == 403
    for replacement in [{"sale_state": "deleted"}, {"revision": True}, {"reason": "  "}, {"extra": 1}]:
        assert api.post(path, headers=ADMIN, json={**body, **replacement}).status_code == 422
    assert change(api, pid="P001-40").status_code == 422
    assert change(api, pid="P999").status_code == 404
    with api.app.state.accounts.repository.connection() as db:
        db.execute("UPDATE accounts SET role='user' WHERE user_id=?", (api.actor,))
    assert api.post(path, headers=ADMIN, json=body).status_code == 403
