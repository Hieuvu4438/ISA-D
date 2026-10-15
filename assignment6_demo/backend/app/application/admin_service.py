from app.domain import ACCESSORY_SIZES, APPAREL_SIZES, SHOE_SIZES, AppError
from app.application.catalog_search import fold
from app.data.variant_repository import product_key


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
            product = products.get(product_key(row["product_id"]))
            if text and text not in fold(f"{row['product_id']} {product['name'] if product else ''}"):
                continue
            if product:
                product["stock_quantity"] = row["quantity"]
                product["sale_state"] = row["sale_state"]
            rows.append({**row, "product": self.products.summary(product) if product else None})
        return {"items": rows[offset:offset + limit], "total": len(rows), "offset": offset, "limit": limit, "revision": snapshot["revision"]}

    def stock(self, actor, product_id, quantity, revision, reason, expected_epoch=None):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        if not self.products.get_by_id(product_key(product_id)):
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm trong danh mục hiện tại.")
        return self.repository.stock(actor, product_id, quantity, revision, reason, expected_epoch=expected_epoch)

    def sale_state(self, actor, product_id, sale_state, revision, reason, expected_epoch=None):
        if not self.products or not self.products.get_by_id(product_id):
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm đã xuất bản.")
        return self.repository.sale_state(actor, product_id, sale_state, revision, reason, expected_epoch=expected_epoch)

    def allocate_variant(self, actor, product_id, size, quantity, revision, reason, expected_epoch=None):
        product = self.products.get_by_id(product_id) if self.products else None
        if not product:
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm trong danh mục hiện tại.")
        allowed = APPAREL_SIZES if product["category"] in {"t_shirt", "jacket"} else SHOE_SIZES if product["category"] in {"running_shoes", "trail_shoes", "casual_shoes", "boots", "sandals"} else ACCESSORY_SIZES
        if size not in allowed:
            raise AppError(422, "SIZE_UNSUPPORTED", "Kích cỡ không phù hợp danh mục: " + ", ".join(sorted(allowed)), "size")
        return self.repository.allocate_variant(actor, product_id, size, quantity, revision, reason, expected_epoch=expected_epoch)
