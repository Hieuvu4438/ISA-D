"""Persist sale state independently of stock, catalog content and order history."""
from app.domain import AppError


def create_availability(db):
    db.execute("""CREATE TABLE IF NOT EXISTS product_availability (
        product_id TEXT PRIMARY KEY, sale_state TEXT NOT NULL CHECK(sale_state IN ('active','archived'))
    )""")


def archived_products(db):
    return {row[0] for row in db.execute("SELECT product_id FROM product_availability WHERE sale_state='archived'")}


def require_saleable(db, product_id):
    row = db.execute("SELECT sale_state FROM product_availability WHERE product_id=?", (product_id,)).fetchone()
    if row and row[0] == "archived":
        raise AppError(409, "PRODUCT_ARCHIVED", "Sản phẩm đã tạm ngừng bán. Hãy xóa khỏi giỏ hoặc chọn sản phẩm khác.", "product_id")
