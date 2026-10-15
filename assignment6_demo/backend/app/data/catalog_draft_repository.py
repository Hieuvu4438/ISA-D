"""Versioned authoring records and tombstones, isolated from published product data."""
from datetime import UTC, datetime
import json

from app.data.admin_repository import AdminRepository
from app.data.purchase_repository import canonical
from app.domain import AppError


class CatalogDraftRepository:
    def __init__(self, accounts):
        self.accounts = accounts
        with accounts.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS catalog_drafts (
                product_id TEXT PRIMARY KEY, version INTEGER NOT NULL CHECK(version>=1),
                base_fingerprint TEXT NOT NULL, payload TEXT, asset TEXT, validation TEXT,
                updated_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS catalog_publication (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), release_path TEXT NOT NULL,
                catalog_fingerprint TEXT NOT NULL, index_fingerprint TEXT NOT NULL, revision INTEGER NOT NULL
            )""")

    def active(self):
        with self.accounts.connection() as db:
            row = db.execute("SELECT * FROM catalog_publication WHERE singleton=1").fetchone()
            return dict(row) if row else None

    def activate(self, actor, product_id, version, base, release, catalog_hash, index_hash, expected_epoch, category_changed=False):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            AdminRepository.require_admin(db, actor, expected_epoch)
            row = self.unpack(db.execute("SELECT * FROM catalog_drafts WHERE product_id=?", (product_id,)).fetchone())
            if not row or not row["payload"] or row["version"] != version:
                raise AppError(409, "DRAFT_CHANGED", "Bản nháp đã thay đổi. Hãy kiểm tra và xuất bản lại.")
            active = db.execute("SELECT * FROM catalog_publication WHERE singleton=1").fetchone()
            if row["base_fingerprint"] != base or active and active["catalog_fingerprint"] != base:
                raise AppError(409, "CATALOG_CHANGED", "Catalog đã đổi. Hãy tải lại và đối chiếu trước khi xuất bản.")
            if category_changed and db.execute("SELECT 1 FROM product_variants WHERE product_id=?", (product_id,)).fetchone():
                raise AppError(409, "CATEGORY_HAS_VARIANTS", "Sản phẩm đã có kích cỡ. Giữ danh mục hiện tại để không làm sai hệ size.")
            revision = active["revision"] + 1 if active else 1
            db.execute("INSERT INTO catalog_publication VALUES(1,?,?,?,?) ON CONFLICT(singleton) DO UPDATE SET release_path=excluded.release_path,catalog_fingerprint=excluded.catalog_fingerprint,index_fingerprint=excluded.index_fingerprint,revision=excluded.revision",
                       (release, catalog_hash, index_hash, revision))
            db.execute("INSERT OR IGNORE INTO inventory VALUES(?,0)", (product_id,))
            db.execute("UPDATE catalog_drafts SET version=version+1,payload=NULL,asset=NULL,validation=NULL WHERE product_id=?", (product_id,))
            # Other drafts remain editable when their base product did not change.
            db.execute("UPDATE catalog_drafts SET base_fingerprint=?,validation=NULL,version=version+1 WHERE product_id<>? AND payload IS NOT NULL AND base_fingerprint=?", (catalog_hash, product_id, base))
            AdminRepository.audit(db, actor, "catalog.publish", product_id, {"catalog_fingerprint": base},
                                  {"catalog_fingerprint": catalog_hash, "index_fingerprint": index_hash, "revision": revision}, "Xuất bản đồng bộ sản phẩm, ảnh và chỉ mục CPU")
        return revision

    @staticmethod
    def unpack(row):
        if row is None:
            return None
        return {**dict(row), **{key: json.loads(row[key]) if row[key] else None for key in ("payload", "asset", "validation")}}

    def get(self, product_id):
        with self.accounts.connection() as db:
            return self.unpack(db.execute("SELECT * FROM catalog_drafts WHERE product_id=?", (product_id,)).fetchone())

    def all(self):
        with self.accounts.connection() as db:
            return [self.unpack(row) for row in db.execute("SELECT * FROM catalog_drafts ORDER BY product_id")]

    def change(self, actor, product_id, version, base, operation, value=None, initial_asset=None, expected_epoch=None):
        with self.accounts.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            AdminRepository.require_admin(db, actor, expected_epoch)
            row = self.unpack(db.execute("SELECT * FROM catalog_drafts WHERE product_id=?", (product_id,)).fetchone())
            current = row["version"] if row else 0
            if current != version:
                raise AppError(409, "DRAFT_CHANGED", "Bản nháp đã thay đổi ở phiên khác. Hãy tải lại trước khi lưu.")
            if row and row["payload"] and row["base_fingerprint"] != base:
                raise AppError(409, "CATALOG_CHANGED", "Catalog gốc đã đổi. Cần đối chiếu bản nháp trước khi tiếp tục.")
            if operation != "save" and (not row or not row["payload"]):
                raise AppError(409, "DRAFT_REQUIRED", "Hãy lưu bản nháp trước khi tải ảnh hoặc kiểm tra.")
            payload = row["payload"] if row else None
            asset = row["asset"] if row and row["payload"] else initial_asset
            validation = None
            if operation == "save":
                payload = value
            elif operation == "image":
                asset = value() if callable(value) else value
                if db.execute("SELECT 1 FROM catalog_drafts WHERE product_id<>? AND payload IS NOT NULL AND json_extract(asset,'$.sha256')=?", (product_id, asset["sha256"])).fetchone():
                    raise AppError(409, "IMAGE_ALREADY_USED", "Ảnh đang được dùng cho bản nháp khác. Hãy dùng ảnh riêng cho mã sản phẩm này.")
            elif operation == "discard":
                payload = asset = None
            elif operation == "validate":
                validation = value
            else:
                raise ValueError("unknown draft operation")
            # Versions survive discard to prevent stale updates after delete/recreate (ABA).
            stamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            db.execute("""INSERT INTO catalog_drafts VALUES(?,?,?,?,?,?,?) ON CONFLICT(product_id)
                          DO UPDATE SET version=excluded.version,base_fingerprint=excluded.base_fingerprint,
                          payload=excluded.payload,asset=excluded.asset,validation=excluded.validation,updated_at=excluded.updated_at""",
                       (product_id, current + 1, base, canonical(payload) if payload else None,
                        canonical(asset) if asset else None, canonical(validation) if validation else None, stamp))
            AdminRepository.audit(db, actor, "catalog.draft." + operation, product_id,
                                  {"version": current, "has_draft": bool(row and row["payload"])},
                                  {"version": current + 1, "has_draft": bool(payload), "asset_sha256": asset.get("sha256") if asset else None},
                                  "Soạn thảo catalog; chưa xuất bản")
            result = self.unpack(db.execute("SELECT * FROM catalog_drafts WHERE product_id=?", (product_id,)).fetchone())
        return result
