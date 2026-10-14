from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.domain import AppError
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
H = {"X-Cortis-Intent": "commerce"}
ADDRESS = {"recipient": "Khách demo", "phone": "0900000000", "address_line": "Địa chỉ kiểm thử", "city": "Thành phố demo"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "purchases.sqlite3"))) as client:
        register(client, "buyer@example.test")
        yield client


def register(api, email):
    response = api.post("/api/v1/auth/register", headers={"X-Cortis-Intent": "account"}, json={"email": email, "display_name": "Buyer", "password": "test checkout passphrase 2026"})
    assert response.status_code == 201
    return response.json()["user"]["user_id"]


def add(api, pid="P001", quantity=1, version=0):
    response = api.post("/api/v1/cart/items", headers=H, json={"product_id": pid, "quantity": quantity, "version": version})
    assert response.status_code == 200, response.text


def quote(api):
    response = api.post("/api/v1/checkout/quote", headers=H, json={})
    assert response.status_code == 200, response.text
    return response.json()["quote"]


def request_body(q):
    return {"quote_id": q["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": ADDRESS}


def place(api, body):
    return api.post("/api/v1/purchases", headers=H, json=body)


def test_atomic_checkout_current_prices_order_history_and_replay(api):
    before = api.get("/api/v1/products/P001").json()["product"]["stock_quantity"]
    add(api, quantity=2)
    q = quote(api)
    assert q["subtotal_vnd"] == 3_600_000 and q["shipping_fee_vnd"] == 0
    assert q["total_vnd"] == q["subtotal_vnd"] + q["shipping_fee_vnd"]
    body = request_body(q)
    result = place(api, body)
    assert result.status_code == 201, result.text
    order = result.json()["order"]
    assert order["status"] == "processing" and order["payment_status"] == "unpaid"
    assert order["demo_order"] is True and order["total_vnd"] == q["total_vnd"]
    assert "user_id" not in order and "customer_id" not in order
    assert api.get("/api/v1/cart").json()["cart"]["items"] == []
    assert api.get("/api/v1/products/P001").json()["product"]["stock_quantity"] == before - 2
    assert api.get("/api/v1/purchases").json()["orders"][0]["order_id"] == order["order_id"]
    assert "shipping_address" not in api.get("/api/v1/purchases").text
    replay = place(api, body)
    assert replay.status_code == 201 and replay.json()["replayed"] is True
    assert replay.json()["order"] == order
    assert api.get("/api/v1/purchases").json()["total"] == 1
    assert api.get("/api/v1/products/P001").json()["product"]["stock_quantity"] == before - 2
    conflict = place(api, {**body, "shipping_address": {**ADDRESS, "recipient": "Khác"}})
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_quote_expiry_supersession_cart_change_and_price_change(api):
    add(api)
    old = quote(api)
    current = quote(api)
    assert place(api, request_body(old)).json()["error"]["code"] == "QUOTE_EXPIRED"
    add(api, quantity=2, version=1)
    assert place(api, request_body(current)).json()["error"]["code"] == "CART_CHANGED"
    q = quote(api)
    with api.app.state.accounts.repository.connection() as db:
        db.execute("UPDATE checkout_quotes SET expires_at=0")
    assert place(api, request_body(q)).json()["error"]["code"] == "QUOTE_EXPIRED"
    service = api.app.state.purchases
    user_id = api.get("/api/v1/auth/me").json()["user"]["user_id"]
    q = service.quote(user_id)
    products = service.catalog()
    products["P001"]["price_vnd"] += 1
    with pytest.raises(AppError) as error:
        service.repository.place(user_id, q["quote_id"], str(uuid4()), ADDRESS, products)
    assert error.value.code == "PRICE_CHANGED"
    assert api.get("/api/v1/cart").json()["cart"]["item_count"] == 2


def test_last_stock_concurrent_checkout_one_winner(api):
    repository = api.app.state.purchases.repository
    with repository.accounts.connection() as db:
        db.execute("UPDATE inventory SET quantity=1 WHERE product_id='P001'")
    first = api.get("/api/v1/auth/me").json()["user"]["user_id"]
    add(api)
    q1 = quote(api)
    second = register(api, "second@example.test")
    add(api)
    q2 = quote(api)
    products = api.app.state.purchases.catalog()
    def operation(pair):
        user_id, q = pair
        try:
            repository.place(user_id, q["quote_id"], str(uuid4()), ADDRESS, products)
            return True
        except AppError as exc:
            assert exc.code == "INSUFFICIENT_STOCK"
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(operation, [(first, q1), (second, q2)])) == 1
    assert repository.snapshot()[0]["P001"] == 0
    with repository.accounts.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM purchases").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM cart_items").fetchone()[0] == 1
    # Stock availability must agree across application APIs, even without an encoder.
    assert api.get("/api/v1/products/P001").json()["product"]["in_stock"] is False
    assert api.get("/api/v1/catalog?q=P001&in_stock=true").json()["total"] == 0
    assert api.get("/api/v1/suggestions?q=P001").json()["products"][0]["in_stock"] is False


def test_mid_transaction_stock_failure_rolls_back_every_line(api):
    repository = api.app.state.purchases.repository
    add(api, "P001")
    add(api, "P002", version=1)
    q = quote(api)
    before = repository.snapshot()[0]["P001"]
    with repository.accounts.connection() as db:
        db.execute("UPDATE inventory SET quantity=0 WHERE product_id='P002'")
    failed = place(api, request_body(q))
    assert failed.status_code == 409
    assert repository.snapshot()[0]["P001"] == before
    assert api.get("/api/v1/cart").json()["cart"]["item_count"] == 2
    assert api.get("/api/v1/purchases").json()["total"] == 0


def test_database_insert_failure_rolls_back_inventory_and_cart(api):
    repository = api.app.state.purchases.repository
    add(api)
    q = quote(api)
    body = request_body(q)
    before = repository.snapshot()
    with repository.accounts.connection() as db:
        db.execute("CREATE TRIGGER fail_order BEFORE INSERT ON purchases BEGIN SELECT RAISE(ABORT,'test failure'); END")
    assert place(api, body).status_code == 500
    assert repository.snapshot() == before
    assert api.get("/api/v1/cart").json()["cart"]["item_count"] == 1
    with repository.accounts.connection() as db:
        db.execute("DROP TRIGGER fail_order")
    assert place(api, body).status_code == 201


def test_cancellation_restocks_once_ownership_and_invalid_transition(api):
    add(api)
    q = quote(api)
    order = place(api, request_body(q)).json()["order"]
    pid = order["order_id"]
    stock = api.app.state.purchases.repository.snapshot()[0]["P001"]
    foreign_user = register(api, "foreign@example.test")
    assert foreign_user
    foreign = api.get(f"/api/v1/purchases/{pid}")
    missing = api.get("/api/v1/purchases/ORD-0000000000000000")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["error"]["message"] == missing.json()["error"]["message"]
    assert api.post(f"/api/v1/purchases/{pid}/cancel", headers=H, json={"version": 0}).status_code == 404
    api.post("/api/v1/auth/login", headers={"X-Cortis-Intent": "account"}, json={"email": "buyer@example.test", "password": "test checkout passphrase 2026"})
    stale = api.post(f"/api/v1/purchases/{pid}/cancel", headers=H, json={"version": 9})
    assert stale.json()["error"]["code"] == "ORDER_CHANGED"
    with api.app.state.accounts.repository.connection() as db:
        db.execute("UPDATE purchases SET status='shipped' WHERE order_id=?", (pid,))
    assert api.post(f"/api/v1/purchases/{pid}/cancel", headers=H, json={"version": 0}).json()["error"]["code"] == "ORDER_NOT_CANCELLABLE"
    with api.app.state.accounts.repository.connection() as db:
        db.execute("UPDATE purchases SET status='processing' WHERE order_id=?", (pid,))
    for _ in range(2):
        cancelled = api.post(f"/api/v1/purchases/{pid}/cancel", headers=H, json={"version": 0})
        assert cancelled.status_code == 200 and cancelled.json()["order"]["status"] == "cancelled"
    assert api.app.state.purchases.repository.snapshot()[0]["P001"] == stock + 1


def test_restart_preserves_inventory_and_idempotency(api):
    add(api)
    body = request_body(quote(api))
    order = place(api, body).json()["order"]
    stock = api.app.state.purchases.repository.snapshot()[0]["P001"]
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=api.app.state.accounts.repository.path))) as fresh:
        fresh.post("/api/v1/auth/login", headers={"X-Cortis-Intent": "account"}, json={"email": "buyer@example.test", "password": "test checkout passphrase 2026"})
        assert fresh.app.state.purchases.repository.snapshot()[0]["P001"] == stock
        assert place(fresh, body).json()["order"] == order


def test_concurrent_same_key_and_cancel_each_change_stock_once(api):
    add(api)
    q = quote(api)
    service = api.app.state.purchases
    user_id = api.get("/api/v1/auth/me").json()["user"]["user_id"]
    before = service.repository.snapshot()[0]["P001"]
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.place(user_id, q["quote_id"], key, ADDRESS), range(2)))
    assert sorted(replayed for _, replayed in results) == [False, True]
    assert results[0][0]["order_id"] == results[1][0]["order_id"]
    assert service.repository.snapshot()[0]["P001"] == before - 1
    pid = results[0][0]["order_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        cancelled = list(pool.map(lambda _: service.repository.cancel(user_id, pid, 0), range(2)))
    assert all(row["status"] == "cancelled" and row["version"] == 1 for row in cancelled)
    assert service.repository.snapshot()[0]["P001"] == before
    register(api, "quote-foreign@example.test")
    assert place(api, request_body(q)).json()["error"]["code"] == "QUOTE_EXPIRED"
    assert api.get(f"/api/v1/purchases/{pid}").status_code == 404
    assert api.get("/api/v1/purchases").json()["total"] == 0


@pytest.mark.parametrize("body", [{"customer_id": "C001"}, {"price": 1}, {"quote_id": "short", "idempotency_key": "short", "shipping_address": ADDRESS}])
def test_input_authority_and_strict_validation(api, body):
    assert place(api, body).status_code == 422


def test_empty_cart_shipping_auth_csrf_and_quote_authority(api):
    assert api.post("/api/v1/checkout/quote", headers=H, json={}).json()["error"]["code"] == "CART_EMPTY"
    assert api.post("/api/v1/checkout/quote", headers=H, json={"user_id": "other"}).status_code == 422
    add(api)
    q = quote(api)
    assert q["shipping_fee_vnd"] == 30_000
    body = request_body(q)
    for address in [{**ADDRESS, "phone": "123"}, {**ADDRESS, "recipient": "  "}, {**ADDRESS, "address_line": "     "}, {**ADDRESS, "extra": "x"}]:
        assert place(api, {**body, "shipping_address": address}).status_code == 422
    assert api.post("/api/v1/purchases", json=body).status_code == 403
    assert api.get("/api/v1/purchases?limit=0").status_code == 422
    assert api.get("/api/v1/purchases?limit=1&limit=2").status_code == 422
    assert api.get("/api/v1/purchases?user_id=other").status_code == 422
    api.post("/api/v1/auth/logout", headers={"X-Cortis-Intent": "account"}, json={})
    assert api.get("/api/v1/purchases").status_code == 401
    assert place(api, body).status_code == 401
