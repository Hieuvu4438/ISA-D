from app.domain import AppError


class ShoppingService:
    def __init__(self, repository, products):
        self.repository = repository
        self.products = products

    def product(self, product_id):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        product = self.products.get_by_id(product_id)
        if product is None:
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
        return product

    def cart(self, user_id):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        version, rows = self.repository.cart(user_id)
        items = []
        for row in rows:
            product = self.products.get_by_id(row["product_id"])
            issue = "PRODUCT_UNAVAILABLE" if product is None else "OUT_OF_STOCK" if product["stock_quantity"] == 0 else "INSUFFICIENT_STOCK" if product["stock_quantity"] < row["quantity"] else None
            price = product["price_vnd"] if product else 0
            items.append({**row, "product": self.products.summary(product) if product else None,
                          "unit_price_vnd": price, "line_total_vnd": price * row["quantity"],
                          "available_quantity": min(99, product["stock_quantity"]) if product else 0, "issue": issue})
        return {"version": version, "items": items, "item_count": sum(row["quantity"] for row in rows),
                "subtotal_vnd": sum(row["line_total_vnd"] for row in items), "currency": "VND",
                "has_issues": any(row["issue"] for row in items), "stock_reserved": False}

    def set_quantity(self, user_id, product_id, quantity, version):
        if quantity:
            product = self.product(product_id)
            if product["stock_quantity"] < quantity:
                raise AppError(409, "INSUFFICIENT_STOCK", "Số lượng vượt tồn kho hiện tại. Hãy chọn số lượng thấp hơn.", "quantity")
        # Zero permits removal of a discontinued product.
        self.repository.set_quantity(user_id, product_id, quantity, version)
        return self.cart(user_id)

    def wishlist(self, user_id):
        items = []
        for product_id in self.repository.wishlist(user_id):
            if not self.products:
                raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
            product = self.products.get_by_id(product_id)
            items.append({"product_id": product_id, "product": self.products.summary(product) if product else None})
        return {"items": items, "total": len(items)}

    def save(self, user_id, product_id, saved):
        if saved:
            self.product(product_id)
        self.repository.save(user_id, product_id, saved)
        return self.wishlist(user_id)
