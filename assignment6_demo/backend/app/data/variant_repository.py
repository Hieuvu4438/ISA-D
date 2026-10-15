"""SKU identity and stock views; existing unsized stock is never guessed into sizes."""
from app.domain import AppError
from app.data.product_availability import create_availability, require_saleable


def line_key(item):
    return item.get("variant_id") or item["product_id"]


def product_key(sku):
    return sku.split("-", 1)[0]


def variants(db, product_id):
    rows = db.execute("""SELECT v.variant_id,v.size,i.quantity AS stock_quantity FROM product_variants v
                         JOIN inventory i ON i.product_id=v.variant_id WHERE v.product_id=? ORDER BY v.rowid""", (product_id,)).fetchall()
    if rows:
        return [dict(row) for row in rows]
    row = db.execute("SELECT quantity FROM inventory WHERE product_id=?", (product_id,)).fetchone()
    return [{"variant_id": product_id, "size": None, "stock_quantity": row[0]}] if row else []


def choose(db, product_id, variant_id=None):
    require_saleable(db, product_id)
    rows = variants(db, product_id)
    if not variant_id:
        if any(row["size"] is not None for row in rows):
            raise AppError(409, "VARIANT_REQUIRED", "Hãy mở sản phẩm và chọn kích cỡ trước khi thêm vào giỏ.", "variant_id")
        variant_id = product_id
    for row in rows:
        if row["variant_id"] == variant_id:
            return row
    raise AppError(409, "VARIANT_UNAVAILABLE", "Biến thể không thuộc sản phẩm hoặc không còn bán. Hãy chọn lại kích cỡ.", "variant_id")


def stock_snapshot(db):
    # Legacy/default stock becomes unallocated when the first explicit size exists.
    rows = db.execute("""SELECT COALESCE(v.product_id,i.product_id) AS parent, SUM(i.quantity) AS quantity
                         FROM inventory i LEFT JOIN product_variants v ON v.variant_id=i.product_id
                         WHERE v.variant_id IS NOT NULL OR NOT EXISTS
                           (SELECT 1 FROM product_variants d WHERE d.product_id=i.product_id)
                         GROUP BY parent""").fetchall()
    return {row[0]: row[1] for row in rows}


class VariantRepository:
    def __init__(self, accounts):
        self.accounts = accounts
        with accounts.connection() as db:
            create_availability(db)
            db.execute("""CREATE TABLE IF NOT EXISTS product_variants (
                variant_id TEXT PRIMARY KEY, product_id TEXT NOT NULL,
                size TEXT NOT NULL, UNIQUE(product_id,size)
            )""")

    def detail(self, product_id):
        rows, revision, _ = self.sale_detail(product_id)
        return rows, revision

    def sale_detail(self, product_id):
        with self.accounts.connection() as db:
            db.execute("BEGIN")
            revision = db.execute("SELECT revision FROM inventory_state WHERE singleton=1").fetchone()[0]
            row = db.execute("SELECT sale_state FROM product_availability WHERE product_id=?", (product_id,)).fetchone()
            return variants(db, product_id), revision, row[0] if row else "active"
