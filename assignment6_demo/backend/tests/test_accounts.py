from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import time

from fastapi.testclient import TestClient
import pytest

from app.application.account_service import hash_password
from app.data.account_repository import AccountRepository
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
HEADERS = {"X-Cortis-Intent": "account"}
PASSWORD = "test account passphrase 2026"


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "accounts.sqlite3"))) as client:
        yield client


def register(api, email="shopper@example.test", **extra):
    return api.post("/api/v1/auth/register", headers=HEADERS, json={
        "email": email, "password": PASSWORD, "display_name": "Khách hàng", **extra,
    })


def test_registration_persistence_cookie_and_private_fields(api):
    response = register(api)
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "user"
    assert set(response.json()["user"]) == {"user_id", "email", "display_name", "role"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=28800" in cookie
    assert response.headers["cache-control"] == "no-store"
    me = api.get("/api/v1/auth/me").json()["user"]
    assert me == response.json()["user"]
    repository = api.app.state.accounts.repository
    row = repository.by_email(me["email"])
    assert row["password_hash"].startswith("scrypt$16384$8$5$")
    assert row["customer_id"] is None and PASSWORD not in row["password_hash"]
    with repository.connection() as db:
        token_hash = db.execute("SELECT token_hash FROM sessions").fetchone()[0]
        assert api.cookies.get("cortis_session") != token_hash
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=repository.path))) as fresh:
        result = fresh.post("/api/v1/auth/login", headers=HEADERS, json={"email": "SHOPPER@EXAMPLE.TEST", "password": PASSWORD})
        assert result.status_code == 200 and result.json()["user"] == me


def test_no_auto_demo_access_and_role_escalation(api):
    assert api.get("/api/v1/orders/O001").status_code == 401
    assert api.get("/api/v1/admin/overview").status_code == 401
    for extra in [{"role": "admin"}, {"customer_id": "C001"}, {"user_id": "admin"}]:
        assert register(api, **extra).status_code == 422
    assert register(api).status_code == 201
    assert api.get("/api/v1/admin/overview").status_code == 403
    assert api.get("/api/v1/orders/O001").status_code == 404
    assert api.get("/api/v1/orders/O999").status_code == 404


def test_explicit_ownership_and_admin_role(api):
    service = api.app.state.accounts
    service.register("owner@example.test", "Owner", PASSWORD, "cli", customer_id="C001")
    service.register("admin@example.test", "Admin", PASSWORD, "cli", role="admin")
    def login(email):
        return api.post("/api/v1/auth/login", headers=HEADERS, json={"email": email, "password": PASSWORD})
    assert login("owner@example.test").status_code == 200
    own = api.get("/api/v1/orders/O001")
    assert own.status_code == 200 and "customer_id" not in own.json()["order"]
    assert api.get("/api/v1/orders/O002").status_code == 404
    assert api.get("/api/v1/orders/O001", headers={"X-Customer-ID": "C002"}).status_code == 422
    assert login("admin@example.test").status_code == 200
    summary = api.get("/api/v1/admin/overview")
    assert summary.status_code == 200 and summary.json()["accounts"] == {"admin": 1, "user": 1}
    assert api.get("/api/v1/orders/O001").status_code == 404


def test_login_rotation_logout_replay_and_expiry(api):
    register(api)
    old = api.cookies.get("cortis_session")
    assert api.post("/api/v1/auth/login", headers=HEADERS, json={"email": "shopper@example.test", "password": PASSWORD}).status_code == 200
    current = api.cookies.get("cortis_session")
    assert old != current
    assert api.get("/api/v1/auth/me", headers={"Cookie": f"cortis_session={old}"}).status_code == 401
    assert api.post("/api/v1/auth/logout", headers=HEADERS, json={}).status_code == 200
    assert api.get("/api/v1/auth/me", headers={"Cookie": f"cortis_session={current}"}).status_code == 401
    assert api.post("/api/v1/auth/logout", headers=HEADERS, json={}).status_code == 200
    repository = api.app.state.accounts.repository
    account = repository.by_email("shopper@example.test")
    repository.issue(account["user_id"], "expired", int(time.time()) - 1)
    assert api.get("/api/v1/auth/me", headers={"Cookie": "cortis_session=expired"}).status_code == 401


def test_password_change_revokes_other_sessions_and_profile(api):
    register(api)
    service = api.app.state.accounts
    account = service.repository.by_email("shopper@example.test")
    other = service.issue(account)
    response = api.post("/api/v1/account/profile", headers=HEADERS, json={"display_name": "  Nguyễn   An  "})
    assert response.json()["user"]["display_name"] == "Nguyễn An"
    for extra in [{"role": "admin"}, {"email": "new@example.test"}]:
        assert api.post("/api/v1/account/profile", headers=HEADERS, json={"display_name": "An", **extra}).status_code == 422
    assert api.post("/api/v1/account/password", headers=HEADERS, json={"current_password": "wrong", "password": PASSWORD + "new"}).status_code == 401
    response = api.post("/api/v1/account/password", headers=HEADERS, json={"current_password": PASSWORD, "password": PASSWORD + "new"})
    assert response.status_code == 200
    assert api.get("/api/v1/auth/me").status_code == 200
    assert api.get("/api/v1/auth/me", headers={"Cookie": f"cortis_session={other}"}).status_code == 401
    assert api.post("/api/v1/auth/login", headers=HEADERS, json={"email": account["email"], "password": PASSWORD}).status_code == 401
    assert api.post("/api/v1/auth/login", headers=HEADERS, json={"email": account["email"], "password": PASSWORD + "new"}).status_code == 200


def test_origin_intent_validation_and_throttling(api):
    body = {"email": "test@example.test", "password": PASSWORD}
    assert api.post("/api/v1/auth/login", json=body).status_code == 403
    assert api.post("/api/v1/auth/login", headers={**HEADERS, "Origin": "https://evil.example"}, json=body).status_code == 403
    assert api.post("/api/v1/auth/login?unknown=1", headers=HEADERS, json=body).status_code == 422
    assert register(api, password="short").status_code == 422
    assert register(api, email="not email").status_code == 422
    assert register(api, display_name="   ").status_code == 422
    assert register(api).status_code == 201
    assert register(api, email=" SHOPPER@EXAMPLE.TEST ").status_code == 409
    for _ in range(10):
        response = api.post("/api/v1/auth/login", headers=HEADERS, json=body)
        assert response.status_code == 401 and response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert api.post("/api/v1/auth/login", headers=HEADERS, json=body).status_code == 429


def test_concurrent_registration_and_throttle_are_atomic(tmp_path):
    repository = AccountRepository(tmp_path / "accounts.sqlite3")
    # Same email races are resolved by the SQL constraint, independently of service pre-checks.
    hashed = hash_password(PASSWORD)
    def create(i):
        try:
            repository.create(str(i), "same@example.test", "Name", hashed, "user")
            return True
        except sqlite3.IntegrityError:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(create, range(8))) == 1
        reservations = list(pool.map(lambda _: repository.throttle([("bucket", 3)], int(time.time())), range(8)))
        assert sum(reservations) == 3


def test_secure_cookie_and_cors(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "db.sqlite3", cookie_secure=True))) as api:
        result = register(api)
        assert "Secure" in result.headers["set-cookie"]
        preflight = api.options("/api/v1/auth/login", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "X-Cortis-Intent,Content-Type"})
        assert preflight.status_code == 200 and preflight.headers["access-control-allow-credentials"] == "true"
