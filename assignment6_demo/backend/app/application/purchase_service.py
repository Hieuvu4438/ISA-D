from app.domain import AppError


class PurchaseService:
    def __init__(self, repository, products):
        self.repository = repository
        self.products = products

    def catalog(self):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")
        result = {p["product_id"]: p for p in self.products.products}
        with self.repository.accounts.connection() as db:
            for row in db.execute("SELECT variant_id,product_id FROM product_variants"):
                if row["product_id"] in result:
                    result[row["variant_id"]] = result[row["product_id"]]
        return result

    def quote(self, user_id, expected_epoch=None):
        return self.repository.quote(user_id, self.catalog(), expected_epoch=expected_epoch)

    def place(self, user_id, quote_id, key, address, expected_epoch=None):
        return self.repository.place(user_id, quote_id, key, address, self.catalog(), expected_epoch=expected_epoch)
