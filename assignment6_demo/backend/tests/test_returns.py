from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain import AppError
from app.main import create_app
from app.settings import Settings
from test_admin_operations import login, PASSWORD, H

CH = {"X-Cortis-Intent": "commerce"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=Path(__file__).resolve().parents[2], load_models=False, account_db_path=tmp_path / "returns.sqlite3"))) as client:
        client.admin_id = client.app.state.accounts.register("admin@example.test", "Operator", PASSWORD, "cli", role="admin")["user_id"]
        client.user_id = client.app.state.accounts.register("buyer@example.test", "Buyer", PASSWORD, "cli")["user_id"]
        yield client


def order(api, quantity=2, products=("P001",), delivered=True):
    login(api, "buyer@example.test")
    for pid in products:
        version = api.get("/api/v1/cart").json()["cart"]["version"]
        assert api.post("/api/v1/cart/items", headers=CH, json={"product_id": pid, "quantity": quantity, "version": version}).status_code == 200
    quote = api.post("/api/v1/checkout/quote", headers=CH, json={}).json()["quote"]
    response = api.post("/api/v1/purchases", headers=CH, json={"quote_id": quote["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": {"recipient": "Buyer demo", "phone": "0900000000", "address_line": "Test demo address", "city": "Demo city"}})
    assert response.status_code == 201
    pid = response.json()["order"]["order_id"]
    if delivered:
        login(api, "admin@example.test")
        for status, version in [("shipped", 0), ("delivered", 1)]:
            assert api.post(f"/api/v1/admin/purchases/{pid}/status", headers=H, json={"status": status, "version": version, "reason": "Demo delivery"}).status_code == 200
        login(api, "buyer@example.test")
    return api.get(f"/api/v1/purchases/{pid}").json()["order"]


def request_body(version=2, quantity=1, items=None):
    return {"version": version, "idempotency_key": str(uuid4()), "reason": "Không vừa kích thước", "items": items or [{"product_id": "P001", "quantity": quantity}]}


def create(api, purchase, body=None):
    response = api.post(f"/api/v1/purchases/{purchase['order_id']}/returns", headers=CH, json=body or request_body())
    assert response.status_code == 201, response.text
    return response.json()["return"]


def advance(api, item, status, receipt=None):
    body = {"status": status, "version": item["version"], "reason": "Operator inspection"}
    if receipt is not None:
        body["receipt"] = receipt
    return api.post(f"/api/v1/admin/returns/{item['return_id']}/status", headers=H, json=body)


def test_partial_return_receipt_and_demo_credit_preserve_order_and_price(api):
    purchase = order(api)
    stock = api.app.state.purchases.repository.snapshot()[0]["P001"]
    item = create(api, purchase)
    view = api.get(f"/api/v1/purchases/{purchase['order_id']}/returns").json()
    assert view["eligibility"]["items"][0]["remaining_quantity"] == 1
    assert item["merchandise_value_vnd"] == purchase["items"][0]["unit_price_vnd"]
    assert "shipping_address" not in json.dumps(view) and "user_id" not in json.dumps(view) and "idempotency_key" not in json.dumps(view)
    login(api, "admin@example.test")
    item = advance(api, item, "approved").json()["return"]
    assert api.app.state.purchases.repository.snapshot()[0]["P001"] == stock
    receipt = [{"product_id": "P001", "restock_quantity": 1}]
    item = advance(api, item, "received", receipt).json()["return"]
    assert api.app.state.purchases.repository.snapshot()[0]["P001"] == stock + 1
    item = advance(api, item, "closed").json()["return"]
    assert item["refund_status"] == "demo_recorded" and item["refund_amount_vnd"] == item["merchandise_value_vnd"]
    login(api, "buyer@example.test")
    assert api.get(f"/api/v1/purchases/{purchase['order_id']}").json()["order"] == purchase
    assert purchase["payment_status"] == "unpaid"
    second = create(api, purchase)
    view = api.get(f"/api/v1/purchases/{purchase['order_id']}/returns").json()
    assert view["eligibility"]["ineligible_reason"] == "quantity_exhausted"
    assert api.post(f"/api/v1/purchases/{purchase['order_id']}/returns", headers=CH, json=request_body()).status_code == 409
    assert api.post(f"/api/v1/returns/{second['return_id']}/withdraw", headers=CH, json={"version": 0}).status_code == 200
    assert api.post(f"/api/v1/returns/{second['return_id']}/withdraw", headers=CH, json={"version": 0}).status_code == 200
    assert create(api, purchase)["return_id"] != second["return_id"]


def test_create_idempotency_replay_survives_window_and_rejects_changed_content(api):
    purchase = order(api)
    body = request_body()
    item = create(api, purchase, body)
    repo = api.app.state.returns
    repo.clock = lambda: datetime.fromisoformat(purchase["delivered_at"].replace("Z", "+00:00")) + timedelta(days=31)
    response = api.post(f"/api/v1/purchases/{purchase['order_id']}/returns", headers=CH, json=body)
    assert response.status_code == 201 and response.json()["replayed"] is True and response.json()["return"]["return_id"] == item["return_id"]
    assert api.post(f"/api/v1/purchases/{purchase['order_id']}/returns", headers=CH, json={**body, "reason": "Nội dung khác"}).status_code == 409
    with repo.accounts.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM purchase_returns").fetchone()[0] == 1


def test_window_boundary_and_audited_delivery_fallback(api):
    purchase = order(api)
    repo = api.app.state.returns
    delivery = datetime.fromisoformat(purchase["delivered_at"].replace("Z", "+00:00"))
    path = f"/api/v1/purchases/{purchase['order_id']}/returns"
    repo.clock = lambda: delivery + timedelta(days=30)
    assert api.get(path).json()["eligibility"]["eligible"] is True
    repo.clock = lambda: delivery + timedelta(days=30, microseconds=1)
    assert api.get(path).json()["eligibility"]["ineligible_reason"] == "window_expired"
    assert api.post(path, headers=CH, json=request_body()).status_code == 409
    with repo.accounts.connection() as db:
        payload = dict(purchase)
        payload.pop("delivered_at")
        db.execute("UPDATE purchases SET payload=? WHERE order_id=?", (json.dumps(payload), purchase["order_id"]))
    repo.clock = lambda: delivery + timedelta(days=1)
    assert api.get(path).json()["eligibility"]["eligible"] is True
    with repo.accounts.connection() as db:
        db.execute("DELETE FROM admin_audit WHERE action='order.status'")
    assert api.get(path).json()["eligibility"]["ineligible_reason"] == "delivery_unconfirmed"


def test_only_delivered_order_and_available_quantities_allowed(api):
    purchase = order(api, delivered=False)
    path = f"/api/v1/purchases/{purchase['order_id']}/returns"
    assert api.get(path).json()["eligibility"]["ineligible_reason"] == "not_delivered"
    assert api.post(path, headers=CH, json=request_body(version=0)).status_code == 409
    purchase = order(api)
    path = f"/api/v1/purchases/{purchase['order_id']}/returns"
    for items in [[{"product_id": "P002", "quantity": 1}], [{"product_id": "P001", "quantity": 3}]]:
        assert api.post(path, headers=CH, json=request_body(items=items)).status_code == 409
    duplicate = [{"product_id": "P001", "quantity": 1}] * 2
    assert api.post(path, headers=CH, json=request_body(items=duplicate)).status_code == 422
    assert api.post(path, headers=CH, json=request_body(version=1)).status_code == 409


def test_owner_isolation_roles_and_strict_inputs(api):
    purchase = order(api)
    item = create(api, purchase)
    path = f"/api/v1/purchases/{purchase['order_id']}/returns"
    for change in [{"quantity": True}, {"quantity": 1.5}, {"quantity": "1"}, {"quantity": 0}, {"quantity": 100}]:
        assert api.post(path, headers=CH, json=request_body(items=[{"product_id": "P001", **change}])).status_code == 422
    for change in [{"items": []}, {"version": True}, {"user_id": api.admin_id}, {"reason": "x\x00z"}]:
        assert api.post(path, headers=CH, json={**request_body(), **change}).status_code == 422
    assert api.get(path + "?extra=1").status_code == 422
    assert api.post(path, json=request_body()).status_code == 403
    assert api.get("/api/v1/admin/returns").status_code == 403
    assert advance(api, item, "approved").status_code == 403
    login(api, "admin@example.test")
    assert api.get(path).status_code == 404  # Admin's customer identity cannot read another customer's returns.
    assert api.post(f"/api/v1/returns/{item['return_id']}/withdraw", headers=CH, json={"version": 0}).status_code == 404
    for suffix in ["limit=0", "offset=-1", "status=bad", "status=", "limit=1&limit=2", "user_id=abc"]:
        assert api.get("/api/v1/admin/returns?" + suffix).status_code == 422
    api.cookies.clear()
    assert api.get(path).status_code == 401 and api.get("/api/v1/admin/returns").status_code == 401


def test_competing_requests_reserve_quantity_once_and_rejection_releases(api):
    purchase = order(api, quantity=1)
    repo = api.app.state.returns
    def attempt(_):
        try:
            return repo.create(api.user_id, purchase["order_id"], 2, str(uuid4()), [{"product_id": "P001", "quantity": 1}], "Concurrent request")[0]
        except AppError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert len([r for r in results if r == 409]) == 1
    item = next(r for r in results if isinstance(r, dict))
    login(api, "admin@example.test")
    assert advance(api, item, "rejected").status_code == 200
    login(api, "buyer@example.test")
    assert create(api, purchase)["status"] == "requested"


def test_receive_replay_does_not_restock_twice_and_conflict_cannot_rewrite(api):
    purchase = order(api)
    item = create(api, purchase)
    login(api, "admin@example.test")
    assert advance(api, item, "received", [{"product_id": "P001", "restock_quantity": 1}]).status_code == 409
    item = advance(api, item, "approved").json()["return"]
    repo = api.app.state.returns
    stock, rev = api.app.state.purchases.repository.snapshot()
    def receive(_):
        return repo.transition(api.admin_id, item["return_id"], "received", 1, "Concurrent receipt", [{"product_id": "P001", "restock_quantity": 1}])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(receive, range(2)))
    assert results[0] == results[1]
    after, revision = api.app.state.purchases.repository.snapshot()
    assert after["P001"] == stock["P001"] + 1 and revision == rev + 1
    assert advance(api, item, "received", [{"product_id": "P001", "restock_quantity": 0}]).status_code == 409
    assert api.post(f"/api/v1/returns/{item['return_id']}/withdraw", headers=CH, json={"version": 1}).status_code == 404
    with repo.accounts.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM admin_audit WHERE action='return.status' AND json_extract(after_json,'$.status')='received'").fetchone()[0] == 1


def test_receipt_quantities_quarantine_and_transaction_rollback(api):
    purchase = order(api, products=("P001", "P002"))
    item = create(api, purchase, request_body(items=[{"product_id": p, "quantity": 1} for p in ("P001", "P002")]))
    login(api, "admin@example.test")
    item = advance(api, item, "approved").json()["return"]
    path = f"/api/v1/admin/returns/{item['return_id']}/status"
    for receipt in [[{"product_id": "P001", "restock_quantity": 1}], [{"product_id": "P001", "restock_quantity": 1}] * 2,
                    [{"product_id": "P001", "restock_quantity": 2}, {"product_id": "P002", "restock_quantity": 0}]]:
        assert advance(api, item, "received", receipt).status_code == 422
    assert api.post(path, headers=H, json={"status": "approved", "version": 1, "reason": "Bad receipt", "receipt": [{"product_id": "P001", "restock_quantity": 0}]}).status_code == 422
    repo = api.app.state.returns
    before = api.app.state.purchases.repository.snapshot()
    with repo.accounts.connection() as db:
        db.execute("CREATE TRIGGER reject_return_audit BEFORE INSERT ON admin_audit WHEN NEW.action='return.status' BEGIN SELECT RAISE(ABORT,'test audit failure'); END;")
    receipt = [{"product_id": "P001", "restock_quantity": 1}, {"product_id": "P002", "restock_quantity": 0}]
    with pytest.raises(Exception, match="test audit failure"):
        repo.transition(api.admin_id, item["return_id"], "received", 1, "Inspection", receipt)
    assert api.app.state.purchases.repository.snapshot() == before
    assert repo.listing(0, 20)["returns"][0]["status"] == "approved"
    with repo.accounts.connection() as db:
        db.execute("DROP TRIGGER reject_return_audit")
    assert advance(api, item, "received", receipt).status_code == 200
    after, _ = api.app.state.purchases.repository.snapshot()
    assert after["P001"] == before[0]["P001"] + 1 and after["P002"] == before[0]["P002"]


def test_admin_permission_rechecked_in_transaction_and_stale_state_rejected(api):
    purchase = order(api)
    item = create(api, purchase)
    repo = api.app.state.returns
    with pytest.raises(AppError) as error:
        repo.transition(api.user_id, item["return_id"], "approved", 0, "Forbidden actor")
    assert error.value.status == 403
    login(api, "admin@example.test")
    assert advance(api, {**item, "version": 1}, "approved").status_code == 409
    approved = advance(api, item, "approved").json()["return"]
    assert advance(api, item, "rejected").status_code == 409
    assert advance(api, approved, "closed").status_code == 409
    login(api, "buyer@example.test")
    assert api.post(f"/api/v1/returns/{item['return_id']}/withdraw", headers=CH, json={"version": 0}).status_code == 409
