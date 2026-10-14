from app.domain import AppError
from app.application.catalog_search import fold


class AdminService:
    def __init__(self, repository, products):
        self.repository = repository
        self.products = products

    def inventory(self, offset, limit, query=""):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        snapshot = self.repository.inventory()
        products = {p["product_id"]: p for p in self.products.products}
        rows = []
        text = fold(query)
        for row in snapshot["rows"]:
            product = products.get(row["product_id"])
            if text and text not in fold(f"{row['product_id']} {product['name'] if product else ''}"):
                continue
            if product:
                product["stock_quantity"] = row["quantity"]
            rows.append({**row, "product": self.products.summary(product) if product else None})
        return {"items": rows[offset:offset + limit], "total": len(rows), "offset": offset, "limit": limit, "revision": snapshot["revision"]}

    def stock(self, actor, product_id, quantity, revision, reason):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        if not self.products.get_by_id(product_id):
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm trong danh mục hiện tại.")
        return self.repository.stock(actor, product_id, quantity, revision, reason)
