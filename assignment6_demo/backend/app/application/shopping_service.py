from app.domain import AppError
from app.data.variant_repository import variants, product_key, stock_snapshot


class ShoppingService:
    def __init__(self, repository, products):
        self.repository = repository
        self.products = products
        self.inventory = None

    def stock_products(self):
        stock = self.inventory.snapshot()[0] if self.inventory else {}
        return stock

    def product(self, product_id):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
        if self.inventory:
            product["stock_quantity"] = self.stock_products().get(product_id, 0)
        return product

    def cart(self, user_id):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        version, rows = self.repository.cart(user_id)
        with self.repository.accounts.connection() as db:
            db.execute("BEGIN")
            stock = stock_snapshot(db) if self.inventory else {}
            sku_rows = {row["product_id"]: variants(db, product_key(row["product_id"])) for row in rows} if self.inventory else {}
        items = []
        for row in rows:
            sku = row["product_id"]
            pid = product_key(sku)
            product = self.products.get_by_id(pid)
            if product and self.inventory:
                product["stock_quantity"] = stock.get(pid, 0)
                product["_variants"] = sku_rows.get(sku, [])
            selected = next((v for v in sku_rows.get(sku, []) if v["variant_id"] == sku), None)
            available = selected["stock_quantity"] if selected else product["stock_quantity"] if product and not self.inventory else 0
            issue = "PRODUCT_UNAVAILABLE" if product is None else "VARIANT_REQUIRED" if self.inventory and not selected else "OUT_OF_STOCK" if available == 0 else "INSUFFICIENT_STOCK" if available < row["quantity"] else None
            price = product["price_vnd"] if product else 0
            items.append({**row, "product_id": pid, "variant_id": sku, "size": selected["size"] if selected else None, "product": self.products.summary(product) if product else None,
                          "unit_price_vnd": price, "line_total_vnd": price * row["quantity"],
                          "available_quantity": min(99, available), "issue": issue})
        return {"version": version, "items": items, "item_count": sum(row["quantity"] for row in rows),
                "subtotal_vnd": sum(row["line_total_vnd"] for row in items), "currency": "VND",
                "has_issues": any(row["issue"] for row in items), "stock_reserved": False}

    def set_quantity(self, user_id, product_id, quantity, version, expected_epoch=None, variant_id=None):
        if quantity:
            product = self.product(product_id)
            if product["stock_quantity"] < quantity:
                raise AppError(409, "INSUFFICIENT_STOCK", "Số lượng vượt tồn kho hiện tại. Hãy chọn số lượng thấp hơn.", "quantity")
        # Zero permits removal of a discontinued product.
        if variant_id and product_key(variant_id) != product_id:
            raise AppError(422, "VALIDATION_ERROR", "Biến thể không thuộc sản phẩm.", "variant_id")
        self.repository.set_quantity(user_id, product_id, quantity, version, expected_epoch=expected_epoch, variant_id=variant_id)
        return self.cart(user_id)

    def wishlist(self, user_id):
        items = []
        stock, _, sizes = self.inventory.snapshot_with_variants() if self.inventory else ({}, None, {})
        for product_id in self.repository.wishlist(user_id):
            if not self.products:
                raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
            product = self.products.get_by_id(product_id)
            if product and self.inventory:
                product["stock_quantity"] = stock.get(product_id, 0)
                product["_variants"] = sizes.get(product_id, [])
            items.append({"product_id": product_id, "product": self.products.summary(product) if product else None})
        return {"items": items, "total": len(items)}

    def save(self, user_id, product_id, saved, expected_epoch=None):
        if saved:
            self.product(product_id)
        self.repository.save(user_id, product_id, saved, expected_epoch=expected_epoch)
        return self.wishlist(user_id)
