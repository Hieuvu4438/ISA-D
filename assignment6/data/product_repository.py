"""Local product catalogue with strict schema and portable image paths."""

from copy import deepcopy
import json
import math
from pathlib import Path


class ProductRepository:
    def __init__(self, path=None, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        self.path = Path(path or self.root / "data/products.json")
        try:
            products = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot load product catalogue: {self.path}") from exc
        if not isinstance(products, list) or not products:
            raise ValueError("product catalogue must be a nonempty list")
        ids = set()
        for p in products:
            required = {"product_id", "name", "brand", "category", "color", "price", "stock", "description", "image"}
            if not isinstance(p, dict) or not required <= p.keys():
                raise ValueError("product is missing required fields")
            identifier = p["product_id"]
            if not isinstance(identifier, int) or isinstance(identifier, bool) or identifier <= 0 or identifier in ids:
                raise ValueError("product IDs must be unique positive integers")
            ids.add(identifier)
            if any(
                not isinstance(p[k], str) or not p[k].strip()
                for k in ["name", "brand", "category", "color", "description", "image"]
            ):
                raise ValueError("product textual fields must be nonempty strings")
            if p["category"] not in {"shoes", "bag", "clothing"}:
                raise ValueError("unsupported product category")
            price, stock = p["price"], p["stock"]
            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0:
                raise ValueError("price must be finite and nonnegative")
            if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
                raise ValueError("stock must be a nonnegative integer")
            image = (self.root / p["image"]).resolve()
            if not image.is_relative_to(self.root) or not image.is_file():
                raise ValueError("product image must exist inside project root")
        self._products = products

    def all_products(self):
        return deepcopy(self._products)

    def get_by_id(self, product_id):
        return next((p for p in self.all_products() if p["product_id"] == product_id), None)
