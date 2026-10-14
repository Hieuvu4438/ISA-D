"""Transactional operational administration with audit and optimistic concurrency."""
from datetime import UTC, datetime
import json

from app.domain import AppError
from app.data.purchase_repository import PurchaseRepository


class AdminRepository:
    def __init__(self, accounts):
        self.accounts = accounts
        with accounts.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS admin_user_versions (
                    user_id TEXT PRIMARY KEY REFERENCES accounts(user_id), version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS admin_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id TEXT NOT NULL REFERENCES accounts(user_id),
                    action TEXT NOT NULL, subject_id TEXT NOT NULL,
                    before_json TEXT NOT NULL, after_json TEXT NOT NULL,
                    reason TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

    @staticmethod
    def require_admin(db, actor):
        row = db.execute("SELECT role FROM accounts WHERE user_id=?", (actor,)).fetchone()
        if not row or row[0] != "admin":
            raise AppError(403, "FORBIDDEN", "Tài khoản không có quyền quản trị.")

    @staticmethod
    def audit(db, actor, action, subject, before, after, reason):
        db.execute("INSERT INTO admin_audit(actor_id,action,subject_id,before_json,after_json,reason,created_at) VALUES(?,?,?,?,?,?,?)",
                   (actor, action, subject, json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False), reason,
                    datetime.now(UTC).isoformat().replace("+00:00", "Z")))

    def inventory(self):
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            revision = db.execute("SELECT revision FROM inventory_state WHERE singleton=1").fetchone()[0]
            return {"rows": [dict(row) for row in db.execute("SELECT product_id,quantity FROM inventory ORDER BY product_id")], "revision": revision}

    def stock(self, actor, product_id, quantity, revision, reason):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_admin(db, actor)
            current = db.execute("SELECT revision FROM inventory_state WHERE singleton=1").fetchone()[0]
            row = db.execute("SELECT quantity FROM inventory WHERE product_id=?", (product_id,)).fetchone()
            if not row:
                raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
            if current != revision:
                raise AppError(409, "INVENTORY_CHANGED", "Tồn kho đã thay đổi. Hãy tải lại trước khi điều chỉnh.")
            if row[0] != quantity:
                db.execute("UPDATE inventory SET quantity=? WHERE product_id=?", (quantity, product_id))
                db.execute("UPDATE inventory_state SET revision=revision+1 WHERE singleton=1")
                self.audit(db, actor, "inventory.set", product_id, {"quantity": row[0]}, {"quantity": quantity}, reason)
                current += 1
            return {"product_id": product_id, "quantity": quantity, "revision": current}

    def users(self, offset, limit, query=""):
        clause = " WHERE instr(lower(a.email),lower(?))>0" if query else ""
        params = [query] if query else []
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM accounts a" + clause, params).fetchone()[0]
            rows = db.execute("""SELECT a.user_id,a.email,a.display_name,a.role,COALESCE(v.version,0) AS version
                                 FROM accounts a LEFT JOIN admin_user_versions v ON a.user_id=v.user_id
                              """ + clause + " ORDER BY a.created_at,a.user_id LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
            return {"users": [dict(row) for row in rows], "total": total, "offset": offset, "limit": limit}

    def role(self, actor, user_id, role, version, reason):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_admin(db, actor)
            target = db.execute("SELECT user_id,email,display_name,role FROM accounts WHERE user_id=?", (user_id,)).fetchone()
            if not target:
                raise AppError(404, "ACCOUNT_NOT_FOUND", "Không tìm thấy tài khoản.")
            if actor == user_id and target["role"] != role:
                raise AppError(409, "SELF_ROLE_CHANGE", "Không thể tự đổi quyền của phiên quản trị hiện tại.")
            stored = db.execute("SELECT version FROM admin_user_versions WHERE user_id=?", (user_id,)).fetchone()
            current = stored[0] if stored else 0
            if version != current:
                raise AppError(409, "ACCOUNT_CHANGED", "Quyền tài khoản đã thay đổi. Hãy tải lại danh sách.")
            if target["role"] != role:
                if target["role"] == "admin" and db.execute("SELECT COUNT(*) FROM accounts WHERE role='admin'").fetchone()[0] <= 1:
                    raise AppError(409, "LAST_ADMIN", "Phải giữ ít nhất một quản trị viên.")
                db.execute("UPDATE accounts SET role=? WHERE user_id=?", (role, user_id))
                db.execute("INSERT INTO admin_user_versions VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET version=excluded.version", (user_id, current + 1))
                db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
                self.audit(db, actor, "account.role", user_id, {"role": target["role"]}, {"role": role}, reason)
                current += 1
            return {**dict(target), "role": role, "version": current}

    def orders(self, offset, limit, status=None):
        clause, params = (" WHERE status=?", [status]) if status else ("", [])
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM purchases" + clause, params).fetchone()[0]
            rows = db.execute("SELECT order_id,status,version,payload FROM purchases" + clause + " ORDER BY rowid DESC LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
            orders = []
            for row in rows:
                payload = json.loads(row["payload"])
                orders.append({"order_id": row["order_id"], "status": row["status"], "version": row["version"],
                               **{key: payload[key] for key in ("date", "total_vnd", "payment_method", "payment_status")},
                               "items": payload["items"]})
            return {"orders": orders, "total": total, "offset": offset, "limit": limit}

    def transition(self, actor, order_id, status, version, reason):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_admin(db, actor)
            row = db.execute("SELECT status,version,payload FROM purchases WHERE order_id=?", (order_id,)).fetchone()
            if not row:
                raise AppError(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
            if row["status"] == status:
                return {"order_id": order_id, "status": status, "version": row["version"]}
            if row["version"] != version:
                raise AppError(409, "ORDER_CHANGED", "Đơn hàng đã thay đổi. Hãy tải lại danh sách.")
            transitions = {"processing": {"shipped", "cancelled"}, "shipped": {"delivered"}, "delivered": set(), "cancelled": set()}
            if status not in transitions[row["status"]]:
                raise AppError(409, "ORDER_TRANSITION_INVALID", "Không thể chuyển trạng thái đơn hàng theo yêu cầu này.")
            if status == "cancelled":
                for item in json.loads(row["payload"])["items"]:
                    db.execute("UPDATE inventory SET quantity=quantity+? WHERE product_id=?", (item["quantity"], item["product_id"]))
                db.execute("UPDATE inventory_state SET revision=revision+1 WHERE singleton=1")
            db.execute("UPDATE purchases SET status=?,version=version+1 WHERE order_id=?", (status, order_id))
            if status == "delivered":
                payload = json.loads(row["payload"])
                payload["delivered_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                db.execute("UPDATE purchases SET payload=? WHERE order_id=?", (json.dumps(payload, ensure_ascii=False), order_id))
            self.audit(db, actor, "order.status", order_id, {"status": row["status"], "version": row["version"]}, {"status": status, "version": row["version"] + 1}, reason)
            return {"order_id": order_id, "status": status, "version": row["version"] + 1}

    def order_detail(self, order_id):
        with self.accounts.connection() as db:
            row = db.execute("SELECT * FROM purchases WHERE order_id=?", (order_id,)).fetchone()
            if not row:
                raise AppError(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
            return PurchaseRepository.public(row)

    def audit_log(self, offset, limit):
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM admin_audit").fetchone()[0]
            rows = db.execute("SELECT * FROM admin_audit ORDER BY audit_id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            return {"events": [{"audit_id": r["audit_id"], "actor_id": r["actor_id"], "action": r["action"], "subject_id": r["subject_id"],
                                "before": json.loads(r["before_json"]), "after": json.loads(r["after_json"]), "reason": r["reason"], "created_at": r["created_at"]} for r in rows],
                    "total": total, "offset": offset, "limit": limit}
