"""Admin authoring and explicit real-encoder preflight, never live publication."""
from datetime import UTC, datetime

from app.application.catalog_search import fold
from app.application.image_service import ImageService
from app.data.product_repository import digest, product_text
from app.data.vector_index import unit
from app.domain import AppError
from app.domain.catalog_draft import METADATA_FIELDS


class CatalogDraftService:
    def __init__(self, repository, products, images, encoder):
        self.repository = repository
        self.products = products
        self.images = images
        self.encoder = encoder

    def require_catalog(self):
        if not self.products:
            raise AppError(503, "CATALOG_UNAVAILABLE", "Danh mục chưa sẵn sàng.")

    def state(self, product_id):
        self.require_catalog()
        source = self.products.get_by_id(product_id)
        row = self.repository.get(product_id)
        return source, row

    def public(self, product_id, source, row):
        saved = bool(row and row["payload"])
        metadata = row["payload"] if saved else {k: source[k] for k in METADATA_FIELDS} if source else None
        asset = row["asset"] if saved else self.products.asset_for_product(product_id)
        return {"product_id": product_id, "version": row["version"] if row else 0, "has_draft": saved,
                "is_new": source is None, "product": metadata,
                "base_catalog_fingerprint": row["base_fingerprint"] if saved else self.products.fingerprint,
                "current_catalog_fingerprint": self.products.fingerprint,
                "image_url": f"/api/v1/admin/products/{product_id}/draft/image?v={row['version']}" if saved and asset else f"/api/v1/media/products/{product_id}" if source else None,
                "image": {k: asset[k] for k in ("source_page", "original_url", "download_url", "transformations", "author", "license", "license_url", "retrieved_at", "sha256", "bytes", "real_photo_review")} if asset else None,
                "validation": row["validation"] if saved else None,
                "updated_at": row["updated_at"] if saved else None, "published": False}

    def detail(self, product_id):
        source, row = self.state(product_id)
        return self.public(product_id, source, row)

    def listing(self, query, status, offset, limit):
        self.require_catalog()
        live = {p["product_id"]: p for p in self.products.products}
        drafts = {row["product_id"]: row for row in self.repository.all()}
        rows = []
        for pid in sorted(set(live) | {pid for pid, row in drafts.items() if row["payload"]}):
            source, draft = live.get(pid), drafts.get(pid)
            saved = bool(draft and draft["payload"])
            metadata = draft["payload"] if saved else source
            if status == "draft" and not saved or status == "live" and source is None:
                continue
            if query and fold(query) not in fold(f"{pid} {metadata['name']} {metadata['brand']}"):
                continue
            rows.append({"product_id": pid, "name": metadata["name"], "category": metadata["category"], "price_vnd": metadata["price_vnd"],
                         "has_draft": saved, "is_new": source is None, "version": draft["version"] if draft else 0})
        return {"items": rows[offset:offset + limit], "total": len(rows), "offset": offset, "limit": limit,
                "catalog_fingerprint": self.products.fingerprint}

    def save(self, actor, product_id, body, expected_epoch):
        source, _ = self.state(product_id)
        if body.base_catalog_fingerprint != self.products.fingerprint:
            raise AppError(409, "CATALOG_CHANGED", "Catalog gốc đã đổi. Hãy tải lại và đối chiếu bản nháp.")
        row = self.repository.change(actor, product_id, body.version, self.products.fingerprint, "save", body.product.model_dump(),
                                     self.products.asset_for_product(product_id), expected_epoch)
        return self.public(product_id, source, row)

    def selected(self, product_id, version):
        source, row = self.state(product_id)
        if not row or not row["payload"]:
            raise AppError(409, "DRAFT_REQUIRED", "Hãy lưu bản nháp trước khi tiếp tục.")
        if row["version"] != version:
            raise AppError(409, "DRAFT_CHANGED", "Bản nháp đã thay đổi. Hãy tải lại trước khi tiếp tục.")
        if row["base_fingerprint"] != self.products.fingerprint:
            raise AppError(409, "CATALOG_CHANGED", "Catalog gốc đã đổi. Cần đối chiếu bản nháp.")
        return source, row

    @staticmethod
    def prepare_image(raw, content_type):
        image, info = ImageService.decode(raw, content_type)
        image.close()
        return info

    def upload(self, actor, product_id, version, provenance, raw, info, expected_epoch):
        source, _ = self.selected(product_id, version)
        def store():
            path, sha = self.images.store(raw, info["format"])
            # A new SKU cannot reuse another catalog photo to inflate product count.
            if any(pid != product_id and value == sha for pid, value in self.products.image_hashes.items()):
                raise AppError(409, "IMAGE_ALREADY_USED", "Ảnh đang gắn với sản phẩm khác. Hãy dùng ảnh chụp riêng cho sản phẩm này.")
            return {**provenance.model_dump(mode="json"), "product_id": product_id, "asset_id": product_id,
                    "local_path": path, "sha256": sha, "bytes": len(raw), "format": info["format"], "width": info["width"], "height": info["height"],
                    "upload_handling": "Giữ nguyên byte tải lên; nguồn và ảnh thật do admin xác nhận",
                    "review_evidence": "admin_visual_attestation", "reviewed_by": actor}
        row = self.repository.change(actor, product_id, version, self.products.fingerprint, "image", store, expected_epoch=expected_epoch)
        return self.public(product_id, source, row)

    def image_file(self, product_id, version=None):
        _, row = self.state(product_id)
        if not row or not row["payload"] or not row["asset"]:
            raise AppError(404, "DRAFT_IMAGE_NOT_FOUND", "Bản nháp chưa có ảnh.")
        if version is not None and row["version"] != version:
            raise AppError(409, "DRAFT_CHANGED", "Ảnh bản nháp đã thay đổi. Hãy tải lại bản nháp.")
        path, raw = self.read_asset(row["asset"])
        decoded, info = ImageService.decode(raw)
        decoded.close()
        return path, {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[info["format"]]

    def read_asset(self, asset):
        # Unedited inherited photos may live in an immutable published release.
        pid = asset.get("product_id")
        if self.products and self.products.image_hashes.get(pid) == asset.get("sha256") and asset.get("local_path", "").startswith("data/images/"):
            path, _, _ = self.products.image_file(pid)
            return path, path.read_bytes()
        return self.images.read(asset)

    def preflight(self, product_id, version):
        _, row = self.selected(product_id, version)
        if not row["asset"]:
            raise AppError(409, "DRAFT_IMAGE_REQUIRED", "Bản nháp cần ảnh thật và đầy đủ nguồn trước khi kiểm tra.")
        if not self.encoder.available:
            raise AppError(503, "MODEL_UNAVAILABLE", "Cần model CPU thật để kiểm tra bản nháp; dữ liệu đã lưu vẫn được giữ.")
        _, raw = self.read_asset(row["asset"])
        image, _ = ImageService.decode(raw)
        text = product_text(row["payload"])
        try:
            self.encoder.validate_text(text)
            text_vector = unit(self.encoder.encode_texts([text]))
            image_vector = unit(self.encoder.encode_images([image]))
            if text_vector.shape != (1, 512) or image_vector.shape != (1, 512):
                raise AppError(500, "INVALID_VECTOR", "Encoder trả sai kích thước batch kiểm tra.")
            unit(0.5 * text_vector + 0.5 * image_vector)
        finally:
            image.close()
        return {"status": "encoder_checked", "model_fingerprint": self.encoder.model_fingerprint,
                "product_fingerprint": digest(row["payload"]), "image_sha256": row["asset"]["sha256"],
                "checked_version": version, "dimension": 512, "device": "cpu",
                "checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "published": False,
                "limitations": ["Không đánh giá độ liên quan", "Chưa build/publish snapshot catalog và index"]}

    def record_preflight(self, actor, product_id, version, validation, expected_epoch):
        source, _ = self.selected(product_id, version)
        row = self.repository.change(actor, product_id, version, self.products.fingerprint, "validate", validation, expected_epoch=expected_epoch)
        return self.public(product_id, source, row)

    def discard(self, actor, product_id, version, expected_epoch):
        source, _ = self.selected(product_id, version)
        row = self.repository.change(actor, product_id, version, self.products.fingerprint, "discard", expected_epoch=expected_epoch)
        return self.public(product_id, source, row)
