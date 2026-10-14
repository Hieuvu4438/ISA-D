"""Owned, quantity-bounded returns with atomic receipt, stock and audit."""
from datetime import UTC, datetime, timedelta
import hashlib
import json
from uuid import uuid4

from app.data.admin_repository import AdminRepository
from app.data.purchase_repository import canonical
from app.domain import AppError

RETURN_DAYS = 30
STATUSES = ("requested", "approved", "rejected", "withdrawn", "received", "closed")


class ReturnRepository:
    def __init__(self, accounts, clock=None):
        self.accounts = accounts
        self.clock = clock or (lambda: datetime.now(UTC))
        with accounts.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS purchase_returns (
                    return_id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES purchases(order_id),
                    user_id TEXT NOT NULL REFERENCES accounts(user_id), idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN
                        ('requested','approved','rejected','withdrawn','received','closed')),
                    version INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL,
                    UNIQUE(user_id,idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS returns_order ON purchase_returns(order_id);
            """)

    @staticmethod
    def public(row):
        return {**json.loads(row["payload"]), "return_id": row["return_id"], "order_id": row["order_id"],
                "status": row["status"], "version": row["version"]}

    @staticmethod
    def owned_order(db, user_id, order_id):
        row = db.execute("SELECT * FROM purchases WHERE user_id=? AND order_id=?", (user_id, order_id)).fetchone()
        if not row:
            raise AppError(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
        return row

    def availability(self, db, order):
        payload = json.loads(order["payload"])
        delivery = payload.get("delivered_at")
        # Orders delivered before timestamp support retain their audited delivery date.
        if not delivery and order["status"] == "delivered":
            event = db.execute("SELECT created_at FROM admin_audit WHERE action='order.status' AND subject_id=? "
                               "AND json_extract(after_json,'$.status')='delivered' ORDER BY audit_id DESC LIMIT 1", (order["order_id"],)).fetchone()
            delivery = event[0] if event else None
        deadline = None
        try:
            delivered = datetime.fromisoformat(delivery.replace("Z", "+00:00"))
            if delivered.tzinfo is None:
                raise ValueError("timezone")
            deadline = delivered + timedelta(days=RETURN_DAYS)
            within = delivered <= self.clock() <= deadline
        except (AttributeError, ValueError, TypeError):
            within = False
        used = {}
        for row in db.execute("SELECT payload FROM purchase_returns WHERE order_id=? AND status NOT IN ('rejected','withdrawn')", (order["order_id"],)):
            for item in json.loads(row[0])["items"]:
                used[item["product_id"]] = used.get(item["product_id"], 0) + item["quantity"]
        items = [{**item, "remaining_quantity": max(0, item["quantity"] - used.get(item["product_id"], 0))} for item in payload["items"]]
        reason = ("not_delivered" if order["status"] != "delivered" else "delivery_unconfirmed" if not delivery
                  else "window_expired" if not within else "quantity_exhausted" if not any(i["remaining_quantity"] for i in items) else None)
        return {"eligible": reason is None, "ineligible_reason": reason,
                "deadline": deadline.isoformat().replace("+00:00", "Z") if deadline else None,
                "window_days": RETURN_DAYS, "policy": "demo_returns_v1", "items": items}

    def order_returns(self, user_id, order_id):
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            order = self.owned_order(db, user_id, order_id)
            rows = db.execute("SELECT * FROM purchase_returns WHERE order_id=? ORDER BY rowid DESC", (order_id,)).fetchall()
            return {"eligibility": self.availability(db, order), "returns": [self.public(row) for row in rows], "order_version": order["version"]}

    def create(self, user_id, order_id, version, key, items, reason, expected_epoch=None):
        items = sorted(items, key=lambda item: item["product_id"])
        request_hash = hashlib.sha256(canonical({"order_id": order_id, "version": version, "items": items, "reason": reason}).encode()).hexdigest()
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.accounts.require_active(db, user_id, expected_epoch)
            order = self.owned_order(db, user_id, order_id)
            previous = db.execute("SELECT * FROM purchase_returns WHERE user_id=? AND idempotency_key=?", (user_id, key)).fetchone()
            if previous:
                if previous["request_hash"] != request_hash:
                    raise AppError(409, "IDEMPOTENCY_CONFLICT", "Mã yêu cầu đã dùng cho nội dung khác. Hãy tải lại danh sách trả hàng.")
                return self.public(previous), True
            if order["version"] != version:
                raise AppError(409, "ORDER_CHANGED", "Đơn hàng đã thay đổi. Hãy tải lại trước khi gửi yêu cầu.")
            available = self.availability(db, order)
            if not available["eligible"]:
                raise AppError(409, "RETURN_INELIGIBLE", "Đơn chưa đủ điều kiện, hết thời hạn hoặc không còn số lượng có thể trả.")
            if db.execute("SELECT COUNT(*) FROM purchase_returns WHERE order_id=?", (order_id,)).fetchone()[0] >= 100:
                raise AppError(429, "RETURN_LIMIT", "Đơn hàng đã đạt giới hạn yêu cầu trả hàng demo.")
            purchased = {item["product_id"]: item for item in available["items"]}
            selected = []
            if len({i["product_id"] for i in items}) != len(items):
                raise AppError(422, "VALIDATION_ERROR", "Không được lặp sản phẩm trong yêu cầu.")
            for item in items:
                source = purchased.get(item["product_id"])
                if not source or item["quantity"] > source["remaining_quantity"]:
                    raise AppError(409, "RETURN_QUANTITY_CHANGED", "Số lượng trả vượt số lượng còn có thể yêu cầu. Hãy tải lại.")
                selected.append({"product_id": item["product_id"], "quantity": item["quantity"],
                                 "product_name": source["product_name"], "unit_price_vnd": source["unit_price_vnd"]})
            stamp = self.clock().isoformat().replace("+00:00", "Z")
            payload = {"items": selected, "reason": reason, "created_at": stamp, "updated_at": stamp,
                       "merchandise_value_vnd": sum(i["unit_price_vnd"] * i["quantity"] for i in selected),
                       "refund_status": "not_processed", "refund_amount_vnd": 0, "demo_return": True}
            return_id = "RMA-" + uuid4().hex[:16].upper()
            db.execute("INSERT INTO purchase_returns VALUES(?,?,?,?,?,?,?,?)", (return_id, order_id, user_id, key, request_hash, "requested", 0, canonical(payload)))
            AdminRepository.audit(db, user_id, "return.request", return_id, {}, {"status": "requested", "items": items}, reason)
            return self.public(db.execute("SELECT * FROM purchase_returns WHERE return_id=?", (return_id,)).fetchone()), False

    def withdraw(self, user_id, return_id, version, expected_epoch=None):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.accounts.require_active(db, user_id, expected_epoch)
            row = db.execute("SELECT * FROM purchase_returns WHERE user_id=? AND return_id=?", (user_id, return_id)).fetchone()
            if not row:
                raise AppError(404, "RETURN_NOT_FOUND", "Không tìm thấy yêu cầu trả hàng.")
            if row["status"] == "withdrawn":
                return self.public(row)
            if row["status"] != "requested" or row["version"] != version:
                raise AppError(409, "RETURN_CHANGED", "Yêu cầu đã được xử lý. Hãy tải lại trạng thái.")
            return self._save(db, row, user_id, "withdrawn", "Khách rút yêu cầu trả hàng", json.loads(row["payload"]))

    def listing(self, offset, limit, status=None):
        clause, params = (" WHERE status=?", [status]) if status else ("", [])
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM purchase_returns" + clause, params).fetchone()[0]
            rows = db.execute("SELECT * FROM purchase_returns" + clause + " ORDER BY rowid DESC LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
            return {"returns": [self.public(row) for row in rows], "total": total, "offset": offset, "limit": limit}

    def transition(self, actor, return_id, status, version, reason, receipt=None, expected_epoch=None):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            AdminRepository.require_admin(db, actor, expected_epoch)
            row = db.execute("SELECT * FROM purchase_returns WHERE return_id=?", (return_id,)).fetchone()
            if not row:
                raise AppError(404, "RETURN_NOT_FOUND", "Không tìm thấy yêu cầu trả hàng.")
            payload = json.loads(row["payload"])
            receipt = sorted(receipt, key=lambda i: i["product_id"]) if receipt is not None else None
            if row["status"] == status:
                if status == "received" and receipt != payload.get("receipt"):
                    raise AppError(409, "RETURN_RECEIPT_CONFLICT", "Yêu cầu đã nhận hàng với kết quả kiểm tra khác.")
                return self.public(row)
            if row["version"] != version:
                raise AppError(409, "RETURN_CHANGED", "Yêu cầu đã thay đổi. Hãy tải lại trước khi xử lý.")
            allowed = {"requested": {"approved", "rejected"}, "approved": {"received", "rejected"}, "received": {"closed"}}
            if status not in allowed.get(row["status"], set()):
                raise AppError(409, "RETURN_TRANSITION_INVALID", "Không thể chuyển trạng thái trả hàng theo yêu cầu này.")
            if status == "received":
                quantities = {i["product_id"]: i["quantity"] for i in payload["items"]}
                if receipt is None or len(receipt) != len(quantities) or {i["product_id"] for i in receipt} != set(quantities):
                    raise AppError(422, "VALIDATION_ERROR", "Cần ghi kết quả kiểm tra cho từng sản phẩm, không lặp hoặc thiếu.")
                restocked = False
                for item in receipt:
                    if item["restock_quantity"] > quantities[item["product_id"]]:
                        raise AppError(422, "VALIDATION_ERROR", "Số lượng nhập lại kho không được vượt số hàng nhận trả.")
                    if item["restock_quantity"]:
                        changed = db.execute("UPDATE inventory SET quantity=quantity+? WHERE product_id=?", (item["restock_quantity"], item["product_id"])).rowcount
                        if not changed:
                            raise AppError(409, "INVENTORY_UNAVAILABLE", "Không tìm thấy mã hàng trong sổ kho. Chưa ghi nhận nhận hàng.")
                        restocked = True
                if restocked:
                    db.execute("UPDATE inventory_state SET revision=revision+1 WHERE singleton=1")
                payload["receipt"] = receipt
            if status == "closed":
                # No payment provider, cash movement or paid assertion occurs here.
                payload.update(refund_status="demo_recorded", refund_amount_vnd=payload["merchandise_value_vnd"])
            payload["operator_note"] = reason
            return self._save(db, row, actor, status, reason, payload)

    def _save(self, db, row, actor, status, reason, payload):
        payload["updated_at"] = self.clock().isoformat().replace("+00:00", "Z")
        db.execute("UPDATE purchase_returns SET status=?,version=version+1,payload=? WHERE return_id=?", (status, canonical(payload), row["return_id"]))
        after = {"status": status, "version": row["version"] + 1}
        if status == "received":
            after["receipt"] = payload["receipt"]
        if status == "closed":
            after.update(refund_status=payload["refund_status"], refund_amount_vnd=payload["refund_amount_vnd"])
        AdminRepository.audit(db, actor, "return.status", row["return_id"], {"status": row["status"], "version": row["version"]}, after, reason)
        return self.public(db.execute("SELECT * FROM purchase_returns WHERE return_id=?", (row["return_id"],)).fetchone())
