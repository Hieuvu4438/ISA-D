from app.domain import AppError


class PurchaseService:
    def __init__(self, repository, products):
        self.repository = repository
        self.products = products

    def catalog(self):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        return {p["product_id"]: p for p in self.products.products}

    def quote(self, user_id):
        return self.repository.quote(user_id, self.catalog())

    def place(self, user_id, quote_id, key, address):
        return self.repository.place(user_id, quote_id, key, address, self.catalog())
