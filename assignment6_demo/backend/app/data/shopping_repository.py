"""Account-scoped shopping lists and optimistic cart updates in SQLite."""
from app.domain import AppError


class ShoppingRepository:
    def __init__(self, accounts):
        self.accounts = accounts
        with accounts.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cart_versions (
                    user_id TEXT PRIMARY KEY REFERENCES accounts(user_id) ON DELETE CASCADE,
                    version INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS cart_items (
                    user_id TEXT NOT NULL REFERENCES accounts(user_id) ON DELETE CASCADE,
                    product_id TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 99),
                    PRIMARY KEY (user_id, product_id)
                );
                CREATE TABLE IF NOT EXISTS wishlist_items (
                    user_id TEXT NOT NULL REFERENCES accounts(user_id) ON DELETE CASCADE,
                    product_id TEXT NOT NULL, PRIMARY KEY (user_id, product_id)
                );
            """)

    def cart(self, user_id):
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            version = db.execute("SELECT version FROM cart_versions WHERE user_id=?", (user_id,)).fetchone()
            rows = db.execute("SELECT product_id,quantity FROM cart_items WHERE user_id=? ORDER BY product_id", (user_id,)).fetchall()
            return version[0] if version else 0, [dict(row) for row in rows]

    def set_quantity(self, user_id, product_id, quantity, version, expected_epoch=None):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.accounts.require_active(db, user_id, expected_epoch)
            db.execute("INSERT OR IGNORE INTO cart_versions(user_id) VALUES (?)", (user_id,))
            current = db.execute("SELECT version FROM cart_versions WHERE user_id=?", (user_id,)).fetchone()[0]
            if current != version:
                raise AppError(409, "CART_CHANGED", "Giỏ hàng đã thay đổi ở phiên khác. Hãy tải lại giỏ hàng.")
            old = db.execute("SELECT quantity FROM cart_items WHERE user_id=? AND product_id=?", (user_id, product_id)).fetchone()
            if quantity and not old:
                count = db.execute("SELECT COUNT(*) FROM cart_items WHERE user_id=?", (user_id,)).fetchone()[0]
                if count >= 100:
                    raise AppError(422, "CART_LIMIT", "Giỏ hàng tối đa 100 sản phẩm khác nhau.")
            if quantity:
                db.execute("INSERT INTO cart_items VALUES (?,?,?) ON CONFLICT(user_id,product_id) DO UPDATE SET quantity=excluded.quantity", (user_id, product_id, quantity))
            else:
                db.execute("DELETE FROM cart_items WHERE user_id=? AND product_id=?", (user_id, product_id))
            if (old[0] if old else 0) != quantity:
                db.execute("UPDATE cart_versions SET version=version+1 WHERE user_id=?", (user_id,))

    def wishlist(self, user_id):
        with self.accounts.connection() as db:
            return [row[0] for row in db.execute("SELECT product_id FROM wishlist_items WHERE user_id=? ORDER BY product_id", (user_id,))]

    def save(self, user_id, product_id, saved, expected_epoch=None):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self.accounts.require_active(db, user_id, expected_epoch)
            if saved:
                exists = db.execute("SELECT 1 FROM wishlist_items WHERE user_id=? AND product_id=?", (user_id, product_id)).fetchone()
                count = db.execute("SELECT COUNT(*) FROM wishlist_items WHERE user_id=?", (user_id,)).fetchone()[0]
                if not exists and count >= 100:
                    raise AppError(422, "WISHLIST_LIMIT", "Danh sách yêu thích tối đa 100 sản phẩm.")
                db.execute("INSERT OR IGNORE INTO wishlist_items VALUES (?,?)", (user_id, product_id))
            else:
                db.execute("DELETE FROM wishlist_items WHERE user_id=? AND product_id=?", (user_id, product_id))
