"""Prepare immutable catalog+index releases; activation is a separate short transaction."""
import json
from pathlib import Path
import re
from uuid import uuid4

from app.application.catalog_search import CatalogSearch
from app.application.index_builder import build_index
from app.application.search_service import SearchService
from app.data.product_repository import ProductRepository
from app.data.vector_index import VectorIndex
from app.domain import AppError


def release_root(root, record):
    if not record:
        return Path(root)
    relative = record["release_path"]
    path = (Path(root) / relative).resolve()
    if not re.fullmatch(r"runtime/catalog/releases/[a-f0-9]{32}", relative) or not path.is_relative_to(Path(root).resolve()) or not path.is_dir():
        raise AppError(503, "CATALOG_RELEASE_UNAVAILABLE", "Phiên bản catalog đã xuất bản không còn khả dụng.")
    return path


class CatalogPublication:
    def __init__(self, root, drafts, services):
        self.root = Path(root).resolve()
        self.drafts = drafts
        self.services = services

    def prepare(self, product_id, version):
        service = self.drafts
        source, row = service.selected(product_id, version)
        encoder = self.services.encoder
        if not encoder.available:
            raise AppError(503, "MODEL_UNAVAILABLE", "Cần model CPU để xuất bản chỉ mục tìm kiếm.")
        if not row["asset"]:
            raise AppError(409, "DRAFT_IMAGE_REQUIRED", "Cần ảnh thật có nguồn trước khi xuất bản.")
        previous = service.products
        previous_index = self.services.index
        base = previous.fingerprint
        directory = self.root / "runtime/catalog/releases" / uuid4().hex
        if not directory.resolve().is_relative_to(self.root):
            raise AppError(503, "CATALOG_RELEASE_UNAVAILABLE", "Thư mục phiên bản catalog không hợp lệ.")
        images = directory / "data/images"
        images.mkdir(parents=True)
        products = {p["product_id"]: p for p in previous.products}
        products[product_id] = {**row["payload"], "product_id": product_id, "stock_quantity": source["stock_quantity"] if source else 0,
                                "image_path": f"data/images/{product_id}.jpg", "image_asset_id": product_id}
        assets = []
        for pid, product in sorted(products.items()):
            if pid == product_id:
                _, raw = service.read_asset(row["asset"])
                asset = {k: v for k, v in row["asset"].items() if k not in ("reviewed_by", "upload_handling")}
                asset["asset_id"] = product_id
            else:
                path, _, _ = previous.image_file(pid)
                raw = path.read_bytes()
                asset = previous.asset_for_product(pid)
            # Immutable byte copies; never modify the seed or an older release's photos.
            (images / f"{pid}.jpg").write_bytes(raw)
            product["image_path"] = f"data/images/{pid}.jpg"
            asset["local_path"] = product["image_path"]
            assets.append(asset)
        (directory / "data/products.json").write_text(json.dumps(list(products.values()), ensure_ascii=False), encoding="utf-8")
        (directory / "data/image_sources.json").write_text(json.dumps({"schema_version": 1, "assets": assets}, ensure_ascii=False), encoding="utf-8")
        repository = ProductRepository(directory)
        meta = build_index(self.root, repository, encoder, previous, previous_index)
        index = VectorIndex(self.root, repository.products, encoder.model_fingerprint)
        if not index.available or index.fingerprint != meta["fingerprint"] or index.catalog_fingerprint != repository.fingerprint:
            raise AppError(503, "INDEX_OUT_OF_SYNC", "Không kích hoạt vì catalog và chỉ mục chưa khớp.")
        search = SearchService(repository, encoder, index, self.root)
        browse = CatalogSearch(repository)
        return {"product_id": product_id, "version": version, "base": base,
                "category_changed": bool(source and source["category"] != row["payload"]["category"]),
                "release_path": directory.relative_to(self.root).as_posix(), "repository": repository,
                "index": index, "search": search, "browse": browse}

    def activate(self, application, prepared, actor, expected_epoch):
        service = self.drafts
        if service.products.fingerprint != prepared["base"]:
            raise AppError(409, "CATALOG_CHANGED", "Catalog đã đổi trong lúc chuẩn bị. Hãy tải lại bản nháp.")
        inventory = application.state.purchases.repository
        prepared["search"].inventory = inventory
        prepared["browse"].inventory = inventory
        revision = service.repository.activate(actor, prepared["product_id"], prepared["version"], prepared["base"], prepared["release_path"],
                                              prepared["repository"].fingerprint, prepared["index"].fingerprint, expected_epoch, prepared["category_changed"])
        # No awaits after durable commit; caller holds the HTTP catalog writer gate.
        products = prepared["repository"]
        self.services.products = products
        self.services.index = prepared["index"]
        self.services.search = prepared["search"]
        self.services.catalog_search = prepared["browse"]
        self.services.errors.pop("products", None)
        for name in ("shopping", "purchases", "admin", "catalog_drafts"):
            getattr(application.state, name).products = products
        return {"published": True, "product_id": prepared["product_id"], "revision": revision,
                "catalog_fingerprint": products.fingerprint, "index_fingerprint": prepared["index"].fingerprint,
                "relevant_available": bool(prepared["search"].policies)}
