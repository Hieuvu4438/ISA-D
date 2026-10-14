from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import time

from fastapi.testclient import TestClient
import pytest

from app.data.account_repository import AccountRepository
from app.data.admin_repository import AdminRepository
from app.domain import AppError
from app.main import create_app
from app.settings import Settings
from test_admin_operations import login, PASSWORD, H

ROOT = Path(__file__).resolve().parents[2]
CH = {"X-Cortis-Intent": "commerce"}
AH = {"X-Cortis-Intent": "account"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "access.sqlite3"))) as client:
        client.admin_id = client.app.state.accounts.register("admin@example.test", "Operator", PASSWORD, "cli", role="admin")["user_id"]
        client.user_id = client.app.state.accounts.register("buyer@example.test", "Buyer", PASSWORD, "cli")["user_id"]
        login(client, "admin@example.test")
        yield client


def access(api, state, version=0, target=None):
    return api.post(f"/api/v1/admin/users/{target or api.user_id}/access", headers=H, json={"access_state": state, "version": version, "reason": "Verified operator decision"})


def test_lock_revokes_all_sessions_unlock_preserves_cart_requires_fresh_auth(api):
    login(api, "buyer@example.test")
    service = api.app.state.accounts
    snapshot = service.repository.by_email("buyer@example.test")
    tokens = [api.cookies.get("cortis_session"), service.issue(snapshot)]
    assert api.post("/api/v1/cart/items", headers=CH, json={"product_id": "P001", "quantity": 1, "version": 0}).status_code == 200
    cart = api.get("/api/v1/cart").json()["cart"]
    login(api, "admin@example.test")
    response = access(api, "locked")
    assert response.status_code == 200
    assert response.json()["user"]["access_state"] == "locked" and response.json()["user"]["version"] == 1
    for token in tokens:
        assert api.get("/api/v1/auth/me", headers={"Cookie": f"cortis_session={token}"}).status_code == 401
    with service.repository.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (api.user_id,)).fetchone()[0] == 0
    locked = api.get("/api/v1/admin/users?access_state=locked").json()
    assert locked["total"] == 1 and locked["users"][0]["user_id"] == api.user_id
    assert "auth_epoch" not in str(locked) and "password_hash" not in str(locked)
    # Correct credentials on a locked account share the generic failure with wrong/missing credentials.
    for email, password in [("buyer@example.test", PASSWORD), ("buyer@example.test", "wrong"), ("missing@example.test", PASSWORD)]:
        result = api.post("/api/v1/auth/login", headers=AH, json={"email": email, "password": password})
        assert result.status_code == 401 and result.json()["error"]["code"] == "INVALID_CREDENTIALS"
        assert result.json()["error"]["message"] == "Email hoặc mật khẩu chưa đúng."
    assert access(api, "active", 1).status_code == 200
    for token in tokens:
        assert api.get("/api/v1/auth/me", headers={"Cookie": f"cortis_session={token}"}).status_code == 401
    with pytest.raises(AppError) as stale:
        service.issue(snapshot)
    assert stale.value.status == 401
    login(api, "buyer@example.test")
    assert api.get("/api/v1/cart").json()["cart"] == cart
    assert set(api.get("/api/v1/auth/me").json()["user"]) == {"user_id", "email", "display_name", "role"}


def test_shared_role_access_version_and_noop_audit(api):
    assert access(api, "active").status_code == 200
    assert api.get("/api/v1/admin/audit").json()["total"] == 0
    assert access(api, "locked").status_code == 200
    assert access(api, "locked").status_code == 409  # A stale request cannot hide an intervening toggle.
    assert access(api, "locked", 1).status_code == 200
    role_path = f"/api/v1/admin/users/{api.user_id}/role"
    assert api.post(role_path, headers=H, json={"role": "admin", "version": 0, "reason": "Old account version"}).status_code == 409
    assert api.post(role_path, headers=H, json={"role": "admin", "version": 1, "reason": "Grant role while access remains locked"}).status_code == 200
    row = api.get("/api/v1/admin/users?q=buyer").json()["users"][0]
    assert row["role"] == "admin" and row["access_state"] == "locked" and row["version"] == 2
    assert access(api, "active", 1).status_code == 409
    assert access(api, "active", 2).status_code == 200
    events = api.get("/api/v1/admin/audit").json()["events"]
    assert len(events) == 3
    assert sum(event["action"] == "account.access" for event in events) == 2


def test_self_guard_and_locked_admin_cannot_mutate(api):
    assert access(api, "locked", target=api.admin_id).json()["error"]["code"] == "SELF_ACCESS_CHANGE"
    second = api.app.state.accounts.register("second@example.test", "Second", PASSWORD, "cli", role="admin")
    assert access(api, "locked", target=second["user_id"]).status_code == 200
    repo = api.app.state.admin.repository
    with pytest.raises(AppError) as failure:
        repo.stock(second["user_id"], "P001", 2, 0, "Locked operator")
    assert failure.value.status == 401
    with repo.accounts.connection() as db:
        assert repo.active_admin_count(db) == 1
    # A trusted stale actor cannot unlock itself either.
    with pytest.raises(AppError):
        repo.access(second["user_id"], second["user_id"], "active", 1, "Not authorized")


def test_audit_failure_rolls_back_access_version_epoch_and_sessions(api):
    service = api.app.state.accounts
    snapshot = service.repository.by_email("buyer@example.test")
    token = service.issue(snapshot)
    with service.repository.connection() as db:
        db.execute("CREATE TRIGGER reject_access_audit BEFORE INSERT ON admin_audit WHEN NEW.action='account.access' BEGIN SELECT RAISE(ABORT,'access audit failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match="access audit failure"):
        api.app.state.admin.repository.access(api.admin_id, api.user_id, "locked", 0, "Atomic operation")
    after = service.repository.by_email("buyer@example.test")
    assert after["access_state"] == "active" and after["auth_epoch"] == snapshot["auth_epoch"]
    assert service.require(token)["user_id"] == api.user_id
    assert api.get("/api/v1/admin/users?q=buyer").json()["users"][0]["version"] == 0


def test_concurrent_role_and_lock_cannot_overwrite_same_account_version(api):
    repo = api.app.state.admin.repository
    def attempt(action):
        try:
            if action == "lock":
                repo.access(api.admin_id, api.user_id, "locked", 0, "Concurrent lock")
            else:
                repo.role(api.admin_id, api.user_id, "admin", 0, "Concurrent role")
            return 200
        except AppError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, ["lock", "role"])) == [200, 409]
    assert api.get("/api/v1/admin/users?q=buyer").json()["users"][0]["version"] == 1
    assert api.get("/api/v1/admin/audit").json()["total"] == 1


USER_WRITES = [
    ("/api/v1/cart/items", CH, {"product_id": "P001", "quantity": 1, "version": 0}),
    ("/api/v1/wishlist/items", CH, {"product_id": "P001", "saved": True}),
    ("/api/v1/checkout/quote", CH, {}),
    ("/api/v1/purchases", CH, {"quote_id": "a" * 32, "idempotency_key": "a" * 32, "shipping_address": {"recipient": "Test demo", "phone": "0900000000", "address_line": "Test demo address", "city": "Demo city"}}),
    ("/api/v1/purchases/ORD-0000000000000000/cancel", CH, {"version": 0}),
    ("/api/v1/purchases/ORD-0000000000000000/returns", CH, {"version": 0, "idempotency_key": "a" * 32, "reason": "Return request", "items": [{"product_id": "P001", "quantity": 1}]}),
    ("/api/v1/returns/RMA-0000000000000000/withdraw", CH, {"version": 0}),
    ("/api/v1/account/profile", AH, {"display_name": "Changed name"}),
    ("/api/v1/account/password", AH, {"current_password": PASSWORD, "password": PASSWORD + "changed"}),
]


@pytest.mark.parametrize("path,headers,body", USER_WRITES)
def test_http_write_rejects_identity_captured_before_lock_then_unlock(api, monkeypatch, path, headers, body):
    login(api, "buyer@example.test")
    service = api.app.state.accounts
    original = service.require
    def capture_then_toggle(token, role=None):
        account = original(token, role)
        repo = api.app.state.admin.repository
        repo.access(api.admin_id, api.user_id, "locked", 0, "Race lock")
        repo.access(api.admin_id, api.user_id, "active", 1, "Race unlock")
        return account  # Simulate the request having authenticated before both writes.
    monkeypatch.setattr(service, "require", capture_then_toggle)
    response = api.post(path, headers=headers, json=body)
    assert response.status_code == 401 and response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert api.app.state.shopping.repository.cart(api.user_id) == (0, [])
    assert api.app.state.shopping.repository.wishlist(api.user_id) == []
    assert service.repository.by_email("buyer@example.test")["display_name"] == "Buyer"
    with service.repository.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM purchases").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM checkout_quotes").fetchone()[0] == 0


@pytest.mark.parametrize("operation", ["stock", "role", "access", "order", "return"])
def test_admin_write_rejects_identity_captured_before_access_revocation(api, monkeypatch, operation):
    service = api.app.state.accounts
    other = service.register("second@example.test", "Second", PASSWORD, "cli", role="admin")
    original = service.require
    def capture_then_toggle(token, role=None):
        account = original(token, role)
        repo = api.app.state.admin.repository
        repo.access(other["user_id"], api.admin_id, "locked", 0, "Race operator lock")
        repo.access(other["user_id"], api.admin_id, "active", 1, "Race operator unlock")
        return account
    monkeypatch.setattr(service, "require", capture_then_toggle)
    cases = {
        "stock": ("/api/v1/admin/inventory/P001", {"quantity": 1, "revision": 0}),
        "role": (f"/api/v1/admin/users/{api.user_id}/role", {"role": "admin", "version": 0}),
        "access": (f"/api/v1/admin/users/{api.user_id}/access", {"access_state": "locked", "version": 0}),
        "order": ("/api/v1/admin/purchases/ORD-0000000000000000/status", {"status": "shipped", "version": 0}),
        "return": ("/api/v1/admin/returns/RMA-0000000000000000/status", {"status": "approved", "version": 0}),
    }
    path, body = cases[operation]
    response = api.post(path, headers=H, json={**body, "reason": "Stale actor request"})
    assert response.status_code == 401 and response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_schema_filter_openapi_and_privilege_guards(api):
    path = f"/api/v1/admin/users/{api.user_id}/access"
    for change in [{"version": True}, {"version": "0"}, {"version": -1}, {"access_state": "disabled"}, {"access_state": False}, {"auth_epoch": 0}, {"reason": "x\x00z"}]:
        assert api.post(path, headers=H, json={"access_state": "locked", "version": 0, "reason": "Test reason", **change}).status_code == 422
    assert api.post(path, json={"access_state": "locked", "version": 0, "reason": "No intent"}).status_code == 403
    for query in ["access_state=", "access_state=bad", "access_state=locked&access_state=active"]:
        assert api.get("/api/v1/admin/users?" + query).status_code == 422
    params = api.get("/openapi.json").json()["paths"]["/api/v1/admin/users"]["get"]["parameters"]
    assert next(p for p in params if p["name"] == "access_state")["schema"]["enum"] == ["active", "locked"]
    login(api, "buyer@example.test")
    assert access(api, "locked", target=api.admin_id).status_code == 403


def test_persistent_default_active_and_stale_password_snapshot_cannot_issue_session(api):
    service = api.app.state.accounts
    snapshot = service.repository.by_email("buyer@example.test")
    assert snapshot["access_state"] == "active" and snapshot["auth_epoch"] == 0
    assert access(api, "locked").status_code == 200
    fresh = AccountRepository(service.repository.path)
    assert fresh.by_email("buyer@example.test")["access_state"] == "locked"
    assert access(api, "active", 1).status_code == 200
    before = fresh.by_email("buyer@example.test")
    updated = service.change_password(before, PASSWORD, PASSWORD + "changed", "cli")
    assert updated["auth_epoch"] == before["auth_epoch"] + 1
    with pytest.raises(AppError):
        service.issue(before)
    assert service.require(service.issue(updated))["user_id"] == api.user_id
    # Even a legacy/manual stale session row cannot bypass the locked-state lookup.
    assert access(api, "locked", 2).status_code == 200
    with fresh.connection() as db:
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (fresh.digest("legacy-stale"), api.user_id, int(time.time()) + 60))
    assert fresh.session("legacy-stale", int(time.time())) is None


def test_upgrade_from_existing_seven_column_accounts_preserves_identity_and_sessions(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    token = "legacy-valid-session"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE accounts(user_id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,role TEXT NOT NULL,customer_id TEXT UNIQUE,created_at INTEGER NOT NULL);
            CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES accounts(user_id),expires_at INTEGER NOT NULL);
        """)
        db.execute("INSERT INTO accounts VALUES(?,?,?,?,?,?,?)", ("legacy-user", "legacy@example.test", "Legacy buyer", "unchanged-test-hash", "user", "C001", 1))
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (AccountRepository.digest(token), "legacy-user", int(time.time()) + 60))
    repo = AccountRepository(path)
    user = repo.by_email("legacy@example.test")
    assert user["access_state"] == "active" and user["auth_epoch"] == 0
    assert user["customer_id"] == "C001" and user["password_hash"] == "unchanged-test-hash"
    assert repo.session(token, int(time.time()))["user_id"] == "legacy-user"
    repo.create("operator", "operator@example.test", "Operator", "test-hash", "admin")
    AdminRepository(repo).access("operator", "legacy-user", "locked", 0, "Upgrade lock test")
    restarted = AccountRepository(path)
    assert restarted.by_email("legacy@example.test")["access_state"] == "locked"
    assert restarted.session(token, int(time.time())) is None
