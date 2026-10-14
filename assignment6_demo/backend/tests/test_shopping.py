from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.application.shopping_service import ShoppingService
from app.domain import AppError
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
HEADERS = {"X-Cortis-Intent": "commerce"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "shopping.sqlite3"))) as client:
        response = client.post("/api/v1/auth/register", headers={"X-Cortis-Intent": "account"}, json={"email": "shopper@example.test", "display_name": "Shopper", "password": "test shopping passphrase 2026"})
        assert response.status_code == 201
        yield client


def update(api, pid="P001", quantity=1, version=0, **extra):
    return api.post("/api/v1/cart/items", headers=HEADERS, json={"product_id": pid, "quantity": quantity, "version": version, **extra})


def test_cart_prices_totals_versions_and_stock_not_reserved(api):
    original = api.get("/api/v1/products/P001").json()["product"]
    empty = api.get("/api/v1/cart")
    assert empty.json()["cart"]["items"] == []
    assert empty.headers["cache-control"] == "no-store"
    assert update(api, quantity=2).status_code == 200
    cart = api.get("/api/v1/cart").json()["cart"]
    assert cart["version"] == 1 and cart["item_count"] == 2
    assert cart["subtotal_vnd"] == 2 * original["price_vnd"]
    assert cart["stock_reserved"] is False
    assert cart["items"][0]["available_quantity"] == original["stock_quantity"]
    assert api.get("/api/v1/products/P001").json()["product"]["stock_quantity"] == original["stock_quantity"]
    assert update(api, quantity=2, version=1).json()["cart"]["version"] == 1  # Desired-state replay is a no-op.
    conflict = update(api, quantity=3, version=0)
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "CART_CHANGED"
    assert update(api, quantity=0, version=1).json()["cart"]["items"] == []
    assert update(api, quantity=0, version=2).json()["cart"]["version"] == 2


@pytest.mark.parametrize("extra", [{"quantity": True}, {"quantity": "1"}, {"quantity": 1.0}, {"quantity": -1}, {"quantity": 100}, {"version": True}, {"version": -1}, {"product_id": "../P001"}, {"price_vnd": 1}, {"user_id": "other"}])
def test_strict_cart_request(api, extra):
    payload = {"product_id": "P001", "quantity": 1, "version": 0, **extra}
    assert api.post("/api/v1/cart/items", headers=HEADERS, json=payload).status_code == 422
    assert api.get("/api/v1/cart").json()["cart"]["items"] == []


def test_missing_product_out_of_stock_and_oversell_input(api):
    assert update(api, pid="P999").status_code == 404
    products = api.app.state.services.products.products
    empty = next(p for p in products if p["stock_quantity"] == 0)
    assert update(api, pid=empty["product_id"]).json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert update(api, quantity=99).status_code == 409
    assert api.get("/api/v1/cart").json()["cart"]["version"] == 0


def test_wishlist_idempotent_and_customer_isolation(api):
    for _ in range(2):
        saved = api.post("/api/v1/wishlist/items", headers=HEADERS, json={"product_id": "P001", "saved": True})
        assert saved.status_code == 200 and saved.json()["total"] == 1
    first_cookie = api.cookies.get("cortis_session")
    update(api)
    response = api.post("/api/v1/auth/register", headers={"X-Cortis-Intent": "account"}, json={"email": "other@example.test", "display_name": "Other", "password": "other test passphrase 2026"})
    assert response.status_code == 201
    assert api.get("/api/v1/wishlist").json()["total"] == 0
    assert api.get("/api/v1/cart").json()["cart"]["items"] == []
    # Registration rotated the old browser session; authenticate first user again.
    assert api.get("/api/v1/cart", headers={"Cookie": f"cortis_session={first_cookie}"}).status_code == 401
    login = api.post("/api/v1/auth/login", headers={"X-Cortis-Intent": "account"}, json={"email": "shopper@example.test", "password": "test shopping passphrase 2026"})
    assert login.status_code == 200
    assert api.get("/api/v1/wishlist").json()["total"] == 1
    assert api.get("/api/v1/cart").json()["cart"]["item_count"] == 1
    assert api.post("/api/v1/wishlist/items", headers=HEADERS, json={"product_id": "P001", "saved": False}).json()["total"] == 0


def test_auth_csrf_query_and_wishlist_validation(api):
    assert api.post("/api/v1/cart/items", json={"product_id": "P001", "quantity": 1, "version": 0}).status_code == 403
    assert api.post("/api/v1/cart/items", headers={**HEADERS, "Origin": "https://evil.example"}, json={"product_id": "P001", "quantity": 1, "version": 0}).status_code == 403
    assert api.get("/api/v1/cart?user_id=other").status_code == 422
    assert api.get("/api/v1/wishlist?customer_id=C001").status_code == 422
    assert api.post("/api/v1/wishlist/items", headers=HEADERS, json={"product_id": "P001", "saved": "true"}).status_code == 422
    assert api.post("/api/v1/wishlist/items", headers=HEADERS, json={"product_id": "P999", "saved": True}).status_code == 404
    assert api.post("/api/v1/wishlist/items", headers=HEADERS, json={"product_id": "P999", "saved": False}).status_code == 200
    api.post("/api/v1/auth/logout", headers={"X-Cortis-Intent": "account"}, json={})
    assert api.get("/api/v1/cart").status_code == 401
    assert api.get("/api/v1/wishlist").status_code == 401
    assert update(api).status_code == 401


def test_concurrent_versions_one_winner_and_cart_persistence(api):
    shopping = api.app.state.shopping
    user_id = api.get("/api/v1/auth/me").json()["user"]["user_id"]
    def operation(quantity):
        try:
            shopping.set_quantity(user_id, "P001", quantity, 0)
            return True
        except AppError as exc:
            assert exc.code == "CART_CHANGED"
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(operation, [1, 2])) == 1
    path = api.app.state.accounts.repository.path
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=path))) as fresh:
        response = fresh.post("/api/v1/auth/login", headers={"X-Cortis-Intent": "account"}, json={"email": "shopper@example.test", "password": "test shopping passphrase 2026"})
        assert response.status_code == 200
        assert fresh.get("/api/v1/cart").json()["cart"]["version"] == 1


def test_catalog_changes_are_reported_prices_recomputed_and_removed_item_recoverable(api):
    base = api.app.state.shopping
    user_id = api.get("/api/v1/auth/me").json()["user"]["user_id"]
    base.set_quantity(user_id, "P001", 2, 0)
    product = base.products.get_by_id("P001")
    product.update(price_vnd=123, stock_quantity=1)
    changed = ShoppingService(base.repository, SimpleNamespace(get_by_id=lambda _: product, summary=base.products.summary))
    cart = changed.cart(user_id)
    assert cart["subtotal_vnd"] == 246 and cart["items"][0]["issue"] == "INSUFFICIENT_STOCK"
    removed = ShoppingService(base.repository, SimpleNamespace(get_by_id=lambda _: None))
    assert removed.cart(user_id)["items"][0]["issue"] == "PRODUCT_UNAVAILABLE"
    assert removed.set_quantity(user_id, "P001", 0, 1)["items"] == []


def test_cart_wishlist_capacity_guards(api):
    repository = api.app.state.shopping.repository
    user_id = api.get("/api/v1/auth/me").json()["user"]["user_id"]
    with repository.accounts.connection() as db:
        db.executemany("INSERT INTO wishlist_items VALUES (?,?)", [(user_id, f"P{i:03}") for i in range(1, 101)])
        db.executemany("INSERT INTO cart_items VALUES (?,?,1)", [(user_id, f"P{i:03}") for i in range(1, 101)])
    with pytest.raises(AppError, match="100"):
        repository.save(user_id, "P101", True)
    with pytest.raises(AppError, match="100"):
        repository.set_quantity(user_id, "P101", 1, 0)
    repository.save(user_id, "P001", True)  # No-op at limit still works.
    repository.set_quantity(user_id, "P001", 0, 0)
    assert len(repository.cart(user_id)[1]) == 99
