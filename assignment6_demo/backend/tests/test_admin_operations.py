from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.domain import AppError
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "test admin operations passphrase 2026"
H = {"X-Cortis-Intent": "admin"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "admin.sqlite3"))) as client:
        admin = client.app.state.accounts.register("admin@example.test", "Operator", PASSWORD, "cli", role="admin")
        user = client.app.state.accounts.register("buyer@example.test", "Buyer", PASSWORD, "cli")
        client.admin_id = admin["user_id"]
        client.user_id = user["user_id"]
        login(client, "admin@example.test")
        yield client


def login(api, email):
    response = api.post("/api/v1/auth/login", headers={"X-Cortis-Intent": "account"}, json={"email": email, "password": PASSWORD})
    assert response.status_code == 200


def place_order(api):
    login(api, "buyer@example.test")
    headers = {"X-Cortis-Intent": "commerce"}
    version = api.get("/api/v1/cart").json()["cart"]["version"]
    assert api.post("/api/v1/cart/items", headers=headers, json={"product_id": "P001", "quantity": 1, "version": version}).status_code == 200
    q = api.post("/api/v1/checkout/quote", headers=headers, json={}).json()["quote"]
    response = api.post("/api/v1/purchases", headers=headers, json={"quote_id": q["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": {"recipient": "Buyer demo", "phone": "0900000000", "address_line": "Test demo address", "city": "Demo city"}})
    assert response.status_code == 201
    order = response.json()["order"]
    login(api, "admin@example.test")
    return order


def test_inventory_update_live_stock_version_noop_and_audit(api):
    snapshot = api.get("/api/v1/admin/inventory?q=P001").json()
    assert snapshot["total"] == 1
    body = {"quantity": 0, "revision": snapshot["revision"], "reason": "Periodic stock count"}
    response = api.post("/api/v1/admin/inventory/P001", headers=H, json=body)
    assert response.status_code == 200
    assert response.json()["inventory"]["revision"] == snapshot["revision"] + 1
    assert api.get("/api/v1/products/P001").json()["product"]["in_stock"] is False
    assert api.get("/api/v1/catalog?q=P001&in_stock=true").json()["total"] == 0
    stale = api.post("/api/v1/admin/inventory/P001", headers=H, json=body)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "INVENTORY_CHANGED"
    body["revision"] += 1
    assert api.post("/api/v1/admin/inventory/P001", headers=H, json=body).status_code == 200
    audit = api.get("/api/v1/admin/audit").json()
    assert audit["total"] == 1
    event = audit["events"][0]
    assert event["actor_id"] == api.admin_id and event["action"] == "inventory.set"
    assert event["after"] == {"quantity": 0} and event["reason"] == body["reason"]


def test_order_fulfillment_state_machine_snapshot_and_privacy(api):
    order = place_order(api)
    pid = order["order_id"]
    assert api.get("/api/v1/admin/overview").json()["orders"] == 31
    rows = api.get("/api/v1/admin/purchases?status=processing").json()
    assert rows["total"] == 1 and "shipping_address" not in rows["orders"][0]
    detail = api.get(f"/api/v1/admin/purchases/{pid}").json()["order"]
    assert detail["shipping_address"]["recipient"] == "Buyer demo"
    assert "user_id" not in detail and "customer_id" not in detail
    path = f"/api/v1/admin/purchases/{pid}/status"
    assert api.post(path, headers=H, json={"status": "delivered", "version": 0, "reason": "Skip disallowed"}).status_code == 409
    for status, version in [("shipped", 0), ("delivered", 1)]:
        response = api.post(path, headers=H, json={"status": status, "version": version, "reason": "Demo fulfillment"})
        assert response.status_code == 200 and response.json()["order"]["version"] == version + 1
    assert api.post(path, headers=H, json={"status": "cancelled", "version": 2, "reason": "Invalid cancellation"}).status_code == 409
    assert api.get("/api/v1/admin/purchases?status=delivered").json()["total"] == 1
    login(api, "buyer@example.test")
    owned = api.get(f"/api/v1/purchases/{pid}").json()["order"]
    assert owned["status"] == "delivered" and owned["payment_status"] == "unpaid"
    assert api.get(f"/api/v1/admin/purchases/{pid}").status_code == 403


def test_admin_cancel_retry_restock_once_and_user_race(api):
    order = place_order(api)
    stock = api.app.state.purchases.repository.snapshot()[0]["P001"]
    repository = api.app.state.admin.repository
    def admin_cancel(_):
        return repository.transition(api.admin_id, order["order_id"], "cancelled", 0, "Demo cancel")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(admin_cancel, range(2)))
    assert all(row["status"] == "cancelled" and row["version"] == 1 for row in results)
    assert api.app.state.purchases.repository.snapshot()[0]["P001"] == stock + 1
    assert api.get("/api/v1/admin/audit").json()["total"] == 1
    assert api.app.state.purchases.repository.cancel(api.user_id, order["order_id"], 0)["status"] == "cancelled"
    assert api.app.state.purchases.repository.snapshot()[0]["P001"] == stock + 1


def test_role_change_revokes_sessions_and_guards_self_and_stale(api):
    login(api, "buyer@example.test")
    old_cookie = api.cookies.get("cortis_session")
    # Keep an independent valid user token so browser-login rotation is not the cause of revocation.
    account = api.app.state.accounts.repository.by_email("buyer@example.test")
    token = api.app.state.accounts.issue(account)
    login(api, "admin@example.test")
    assert old_cookie
    rows = api.get("/api/v1/admin/users").json()["users"]
    assert all(set(row) == {"user_id", "email", "display_name", "role", "version", "access_state"} for row in rows)
    body = {"role": "admin", "version": 0, "reason": "Promote approved operator"}
    response = api.post(f"/api/v1/admin/users/{api.user_id}/role", headers=H, json=body)
    assert response.status_code == 200 and response.json()["user"]["version"] == 1
    assert api.get("/api/v1/auth/me", headers={"Cookie": f"cortis_session={token}"}).status_code == 401
    stale = api.post(f"/api/v1/admin/users/{api.user_id}/role", headers=H, json={**body, "role": "user"})
    assert stale.json()["error"]["code"] == "ACCOUNT_CHANGED"
    own = api.post(f"/api/v1/admin/users/{api.admin_id}/role", headers=H, json={**body, "role": "user"})
    assert own.json()["error"]["code"] == "SELF_ROLE_CHANGE"
    assert api.app.state.accounts.repository.by_email("admin@example.test")["role"] == "admin"
    login(api, "buyer@example.test")
    assert api.get("/api/v1/admin/users").status_code == 200


def test_permission_rechecked_inside_transaction_and_inventory_race(api):
    repository = api.app.state.admin.repository
    revision = repository.inventory()["revision"]
    def change(quantity):
        try:
            repository.stock(api.admin_id, "P001", quantity, revision, "Concurrent stock check")
            return True
        except AppError as exc:
            assert exc.code == "INVENTORY_CHANGED"
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(change, [2, 3])) == 1
    with repository.accounts.connection() as db:
        db.execute("UPDATE accounts SET role='user' WHERE user_id=?", (api.admin_id,))
    with pytest.raises(AppError) as failure:
        repository.stock(api.admin_id, "P001", 9, revision + 1, "Should be denied")
    assert failure.value.code == "FORBIDDEN"


def test_audit_failure_rolls_back_inventory_and_revision(api):
    repository = api.app.state.admin.repository
    before = api.app.state.purchases.repository.snapshot()
    with repository.accounts.connection() as db:
        db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON admin_audit BEGIN SELECT RAISE(ABORT,'test failure'); END")
    response = api.post("/api/v1/admin/inventory/P001", headers=H, json={"quantity": 0, "revision": before[1], "reason": "Rollback test"})
    assert response.status_code == 500
    assert api.app.state.purchases.repository.snapshot() == before
    assert api.get("/api/v1/admin/audit").json()["total"] == 0


@pytest.mark.parametrize("path", ["inventory", "users", "purchases", "audit"])
def test_users_and_anonymous_cannot_read_admin_data(api, path):
    login(api, "buyer@example.test")
    assert api.get("/api/v1/admin/" + path).status_code == 403
    api.post("/api/v1/auth/logout", headers={"X-Cortis-Intent": "account"}, json={})
    assert api.get("/api/v1/admin/" + path).status_code == 401


def test_strict_mutations_and_pagination_security(api):
    base = {"quantity": 1, "revision": 0, "reason": "Inventory test"}
    path = "/api/v1/admin/inventory/P001"
    for bad in [{"quantity": True}, {"quantity": -1}, {"quantity": "1"}, {"quantity": 1_000_001}, {"revision": True}, {"revision": 10**100}, {"reason": "  "}, {"reason": "bad\x00reason"}, {"actor_id": api.admin_id}]:
        assert api.post(path, headers=H, json={**base, **bad}).status_code == 422
    assert api.post(path, json=base).status_code == 403
    assert api.post(path, headers={**H, "Origin": "https://evil.example"}, json=base).status_code == 403
    assert api.get("/api/v1/admin/inventory?limit=0").status_code == 422
    assert api.get("/api/v1/admin/users?limit=1&limit=2").status_code == 422
    assert api.get("/api/v1/admin/purchases?status=wrong").status_code == 422
    assert api.get("/api/v1/admin/audit?actor_id=forged").status_code == 422
    assert api.post("/api/v1/admin/inventory/P999", headers=H, json=base).status_code == 404
    login(api, "buyer@example.test")
    assert api.post(path, headers=H, json=base).status_code == 403


def test_admin_openapi_queries_and_dependency_error_not_missing_product(api):
    from app.application.admin_service import AdminService

    schema = api.get("/openapi.json").json()
    for section in ("inventory", "users", "purchases", "audit"):
        parameters = {r["name"]: r["schema"] for r in schema["paths"][f"/api/v1/admin/{section}"]["get"]["parameters"]}
        assert parameters["limit"]["maximum"] == 100
        assert parameters["offset"]["default"] == 0
        if section in ("inventory", "users"):
            assert parameters["q"]["maxLength"] == 120
    broken = AdminService(api.app.state.admin.repository, None)
    with pytest.raises(AppError) as failure:
        broken.stock(api.admin_id, "P001", 1, 0, "Should fail dependency")
    assert failure.value.code == "CATALOG_UNAVAILABLE" and failure.value.status == 503
    assert api.get("/api/v1/admin/users?q=BUYER%40EXAMPLE.TEST").json()["total"] == 1
