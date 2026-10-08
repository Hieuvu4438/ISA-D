import copy
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from app.domain import AppError

CATEGORIES = {
    "running_shoes": "Giày chạy bộ",
    "trail_shoes": "Giày chạy địa hình",
    "casual_shoes": "Giày thường ngày",
    "bag": "Túi",
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def catalog_fingerprint(products):
    return digest(sorted(products, key=lambda p: p["product_id"]))


def product_text(product):
    return f"{product['name']}. Thương hiệu: {product['brand']}. Loại: {CATEGORIES[product['category']]}. Màu: {product['color']}. {product['description']}"


class ProductRepository:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        try:
            products = json.loads((self.root / "data/products.json").read_text(encoding="utf-8"))
            manifest = json.loads((self.root / "data/image_sources.json").read_text(encoding="utf-8"))
            if not isinstance(products, list) or manifest["schema_version"] != 1:
                raise ValueError("schema")
            assets = {a["asset_id"]: a for a in manifest["assets"]}
            if len(assets) != len(manifest["assets"]):
                raise ValueError("duplicate assets")
            ids, hashes = set(), {}
            expected = {
                "product_id",
                "name",
                "brand",
                "category",
                "color",
                "price_vnd",
                "stock_quantity",
                "description",
                "image_path",
                "image_asset_id",
            }
            for p in products:
                if set(p) != expected or not re.fullmatch(r"P[0-9]{3}", p["product_id"]) or p["product_id"] in ids:
                    raise ValueError("product schema")
                ids.add(p["product_id"])
                for field, maximum in [("name", 120), ("description", 500), ("brand", 120), ("color", 120)]:
                    value = p[field]
                    if (
                        not isinstance(value, str)
                        or not value.strip()
                        or len(value) > maximum
                        or unicodedata.normalize("NFC", value) != value
                    ):
                        raise ValueError("text")
                if p["category"] not in CATEGORIES:
                    raise ValueError("category")
                for field, maximum in [("price_vnd", 1_000_000_000), ("stock_quantity", 1_000_000)]:
                    if type(p[field]) is not int or not 0 <= p[field] <= maximum:
                        raise ValueError("integer")
                path = self._safe_path(p["image_path"])
                asset = assets[p["image_asset_id"]]
                if (
                    asset["product_id"] != p["product_id"]
                    or asset["local_path"] != p["image_path"]
                    or asset["real_photo_review"] != "passed"
                ):
                    raise ValueError("provenance")
                for field in ["source_page", "license_url", "download_url", "original_url"]:
                    parsed = urlparse(asset[field])
                    if parsed.scheme != "https" or not parsed.netloc:
                        raise ValueError("source url")
                if not asset.get("author") or not asset.get("license"):
                    raise ValueError("credit")
                raw = path.read_bytes()
                sha = hashlib.sha256(raw).hexdigest()
                if sha != asset["sha256"] or len(raw) != asset["bytes"]:
                    raise ValueError("checksum")
                with Image.open(path) as image:
                    if (
                        image.format not in ("JPEG", "PNG", "WEBP")
                        or image.width * image.height > 16_000_000
                        or max(image.size) > 8192
                    ):
                        raise ValueError("image")
                    image.verify()
                hashes[p["product_id"]] = sha
            self._products = sorted(products, key=lambda p: p["product_id"])
            self._by_id = {p["product_id"]: p for p in self._products}
            self._assets = assets
            self.image_hashes = hashes
            self.fingerprint = digest({"products": self._products, "image_sha256_by_id": hashes})
        except Exception as exc:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Dữ liệu sản phẩm chưa sẵn sàng.") from exc

    def _safe_path(self, value):
        path = (self.root / value).resolve()
        image_root = (self.root / "data/images").resolve()
        if (
            not isinstance(value, str)
            or Path(value).is_absolute()
            or not image_root.is_relative_to(self.root)
            or not path.is_relative_to(image_root)
            or not path.is_file()
        ):
            raise ValueError("unsafe image path")
        return path

    @property
    def products(self):
        return self.all_products()

    def all_products(self):
        return copy.deepcopy(self._products)

    def get_by_id(self, product_id):
        return copy.deepcopy(self._by_id.get(product_id))

    def _credit(self, product):
        asset = self._assets[product["image_asset_id"]]
        changes = asset.get("transformations", [])
        return {
            **{f: asset[f] for f in ("source_page", "author", "license", "license_url")},
            "transformations": [changes] if isinstance(changes, str) else list(changes),
        }

    def summary(self, product):
        return {
            **{f: product[f] for f in ("product_id", "name", "category", "brand", "color", "price_vnd")},
            "in_stock": product["stock_quantity"] > 0,
            "image_url": f"/api/v1/media/products/{product['product_id']}",
        }

    def detail(self, product):
        return {
            **self.summary(product),
            "description": product["description"],
            "stock_quantity": product["stock_quantity"],
            "image_credit": self._credit(product),
        }

    def credits(self):
        return [
            {"asset_id": p["image_asset_id"], "product_id": p["product_id"], **self._credit(p)} for p in self._products
        ]

    def image_file(self, product_id):
        product = self._by_id.get(product_id)
        if product is None:
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
        try:
            path = self._safe_path(product["image_path"])
            raw = path.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
            if checksum != self.image_hashes[product_id]:
                raise ValueError("changed image")
            with Image.open(path) as image:
                mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[image.format]
                image.verify()
            return path, mime, checksum
        except Exception as exc:
            raise AppError(503, "PRODUCT_IMAGE_UNAVAILABLE", "Ảnh sản phẩm chưa sẵn sàng.") from exc
