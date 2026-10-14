"""SQLite inventory, checkout quotes and atomic order placement/cancellation."""
from datetime import UTC, datetime
import hashlib
import json
import secrets
import time
from uuid import uuid4

from app.domain import AppError


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class PurchaseRepository:
    def __init__(self, accounts, products):
        self.accounts = accounts
        with accounts.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS inventory (
                    product_id TEXT PRIMARY KEY, quantity INTEGER NOT NULL CHECK(quantity>=0)
                );
                CREATE TABLE IF NOT EXISTS inventory_state (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO inventory_state VALUES(1,0);
                CREATE TABLE IF NOT EXISTS checkout_quotes (
                    quote_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES accounts(user_id),
                    cart_version INTEGER NOT NULL, payload TEXT NOT NULL, expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS purchases (
                    order_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES accounts(user_id),
                    idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('processing','shipped','delivered','cancelled')),
                    version INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL,
                    UNIQUE(user_id,idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS purchases_owner ON purchases(user_id,order_id);
            """)
            # A restart must never reset quantities consumed by existing orders.
            db.executemany("INSERT OR IGNORE INTO inventory VALUES (?,?)",
                           [(p["product_id"], p["stock_quantity"]) for p in products])

    def snapshot(self):
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            revision = db.execute("SELECT revision FROM inventory_state WHERE singleton=1").fetchone()[0]
            return {row[0]: row[1] for row in db.execute("SELECT product_id,quantity FROM inventory")}, revision

    @staticmethod
    def quote_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def public(row):
        payload = json.loads(row["payload"])
        return {**payload, "order_id": row["order_id"], "status": row["status"], "version": row["version"]}

    def quote(self, user_id, products, expected_epoch=None):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.accounts.require_active(db, user_id, expected_epoch)
            version = db.execute("SELECT version FROM cart_versions WHERE user_id=?", (user_id,)).fetchone()
            rows = db.execute("SELECT product_id,quantity FROM cart_items WHERE user_id=? ORDER BY product_id", (user_id,)).fetchall()
            if not rows:
                raise AppError(409, "CART_EMPTY", "Giỏ hàng đang trống. Hãy chọn sản phẩm trước khi đặt đơn.")
            items = []
            for row in rows:
                pid, quantity = row
                product = products.get(pid)
                stock = db.execute("SELECT quantity FROM inventory WHERE product_id=?", (pid,)).fetchone()
                if not product:
                    raise AppError(409, "PRODUCT_UNAVAILABLE", "Sản phẩm không còn khả dụng. Hãy cập nhật giỏ hàng.")
                if not stock or stock[0] < quantity:
                    raise AppError(409, "INSUFFICIENT_STOCK", "Tồn kho đã thay đổi. Hãy cập nhật giỏ hàng.")
                items.append({"product_id": pid, "product_name": product["name"], "quantity": quantity,
                              "unit_price_vnd": product["price_vnd"], "line_total_vnd": product["price_vnd"] * quantity})
            subtotal = sum(row["line_total_vnd"] for row in items)
            shipping = 0 if subtotal >= 2_000_000 else 30_000
            payload = {"items": items, "subtotal_vnd": subtotal, "shipping_fee_vnd": shipping,
                       "total_vnd": subtotal + shipping, "currency": "VND", "payment_method": "cod",
                       "pricing_policy": "demo_cod_shipping_v1"}
            token = secrets.token_urlsafe(32)
            expires_at = int(time.time()) + 600
            db.execute("DELETE FROM checkout_quotes WHERE expires_at<=?", (int(time.time()),))
            # Keep one current quote per account, bounded storage and explicit supersession.
            db.execute("DELETE FROM checkout_quotes WHERE user_id=?", (user_id,))
            db.execute("INSERT INTO checkout_quotes VALUES(?,?,?,?,?)",
                       (self.quote_hash(token), user_id, version[0] if version else 0, canonical(payload), expires_at))
            return {**payload, "quote_id": token, "cart_version": version[0] if version else 0, "expires_at": expires_at}

    def place(self, user_id, quote_id, key, shipping_address, products, expected_epoch=None):
        request_hash = hashlib.sha256(canonical({"quote_id": quote_id, "shipping_address": shipping_address}).encode()).hexdigest()
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.accounts.require_active(db, user_id, expected_epoch)
            previous = db.execute("SELECT * FROM purchases WHERE user_id=? AND idempotency_key=?", (user_id, key)).fetchone()
            if previous:
                if previous["request_hash"] != request_hash:
                    raise AppError(409, "IDEMPOTENCY_CONFLICT", "Mã xác nhận đã dùng cho nội dung khác. Hãy tải lại checkout.")
                return self.public(previous), True
            quote = db.execute("SELECT * FROM checkout_quotes WHERE user_id=? AND quote_hash=?", (user_id, self.quote_hash(quote_id))).fetchone()
            if not quote or quote["expires_at"] <= int(time.time()):
                raise AppError(409, "QUOTE_EXPIRED", "Báo giá đã hết hạn hoặc được thay thế. Hãy lấy báo giá mới.")
            version = db.execute("SELECT version FROM cart_versions WHERE user_id=?", (user_id,)).fetchone()
            if not version or version[0] != quote["cart_version"]:
                raise AppError(409, "CART_CHANGED", "Giỏ hàng đã thay đổi. Hãy kiểm tra báo giá mới.")
            payload = json.loads(quote["payload"])
            cart = {row[0]: row[1] for row in db.execute("SELECT product_id,quantity FROM cart_items WHERE user_id=?", (user_id,))}
            if cart != {row["product_id"]: row["quantity"] for row in payload["items"]}:
                raise AppError(409, "CART_CHANGED", "Giỏ hàng đã thay đổi. Hãy kiểm tra báo giá mới.")
            for item in payload["items"]:
                product = products.get(item["product_id"])
                if not product or product["price_vnd"] != item["unit_price_vnd"] or product["name"] != item["product_name"]:
                    raise AppError(409, "PRICE_CHANGED", "Thông tin hoặc giá đã thay đổi. Hãy kiểm tra báo giá mới.")
                changed = db.execute("UPDATE inventory SET quantity=quantity-? WHERE product_id=? AND quantity>=?",
                                     (item["quantity"], item["product_id"], item["quantity"])).rowcount
                if not changed:
                    raise AppError(409, "INSUFFICIENT_STOCK", "Sản phẩm vừa hết hàng. Hãy cập nhật giỏ hàng.")
            order_id = "ORD-" + uuid4().hex[:16].upper()
            payload.update(date=datetime.now(UTC).isoformat().replace("+00:00", "Z"), shipping_address=shipping_address,
                           payment_status="unpaid", demo_order=True)
            db.execute("INSERT INTO purchases VALUES(?,?,?,?,?,?,?)", (order_id, user_id, key, request_hash, "processing", 0, canonical(payload)))
            db.execute("DELETE FROM cart_items WHERE user_id=?", (user_id,))
            db.execute("UPDATE cart_versions SET version=version+1 WHERE user_id=?", (user_id,))
            db.execute("UPDATE inventory_state SET revision=revision+1 WHERE singleton=1")
            row = db.execute("SELECT * FROM purchases WHERE order_id=?", (order_id,)).fetchone()
            return self.public(row), False

    def detail(self, user_id, order_id):
        with self.accounts.connection() as db:
            row = db.execute("SELECT * FROM purchases WHERE user_id=? AND order_id=?", (user_id, order_id)).fetchone()
            if not row:
                raise AppError(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
            return self.public(row)

    def history(self, user_id, offset, limit):
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM purchases WHERE user_id=?", (user_id,)).fetchone()[0]
            rows = db.execute("SELECT * FROM purchases WHERE user_id=? ORDER BY rowid DESC LIMIT ? OFFSET ?", (user_id, limit, offset)).fetchall()
            orders = [{k: v for k, v in self.public(row).items() if k in ("order_id", "status", "version", "date", "total_vnd", "payment_method", "payment_status", "demo_order")} for row in rows]
            return {"orders": orders, "total": total, "offset": offset, "limit": limit}

    def cancel(self, user_id, order_id, version, expected_epoch=None):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.accounts.require_active(db, user_id, expected_epoch)
            row = db.execute("SELECT * FROM purchases WHERE user_id=? AND order_id=?", (user_id, order_id)).fetchone()
            if not row:
                raise AppError(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
            if row["status"] == "cancelled":
                return self.public(row)
            if row["status"] != "processing":
                raise AppError(409, "ORDER_NOT_CANCELLABLE", "Đơn đã chuyển sang giao hàng, không thể hủy trực tiếp.")
            if row["version"] != version:
                raise AppError(409, "ORDER_CHANGED", "Đơn hàng đã thay đổi. Hãy tải lại chi tiết.")
            for item in json.loads(row["payload"])["items"]:
                db.execute("UPDATE inventory SET quantity=quantity+? WHERE product_id=?", (item["quantity"], item["product_id"]))
            db.execute("UPDATE purchases SET status='cancelled',version=version+1 WHERE order_id=?", (order_id,))
            db.execute("UPDATE inventory_state SET revision=revision+1 WHERE singleton=1")
            return self.public(db.execute("SELECT * FROM purchases WHERE order_id=?", (order_id,)).fetchone())
