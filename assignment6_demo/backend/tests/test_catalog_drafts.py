"""Private authoring lifecycle with actual SQLite/photos and explicit encoder doubles."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import threading
import time

from fastapi.testclient import TestClient
import numpy as np
import pytest

from app.data.draft_image_storage import DraftImageStorage
from app.domain import AppError
from app.domain.catalog_draft import DraftSave
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
H = {"X-Cortis-Intent": "admin"}
AUTH = {"X-Cortis-Intent": "account"}
ENDPOINT = "/api/v1/admin/products/P001/draft"


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "drafts.sqlite3"))) as client:
        result = client.post("/api/v1/auth/register", headers=AUTH, json={"email": "author@example.test", "password": "authoring passphrase 2026 test", "display_name": "Editor"})
        client.actor = result.json()["user"]["user_id"]
        with client.app.state.accounts.repository.connection() as db:
            db.execute("UPDATE accounts SET role='admin' WHERE user_id=?", (client.actor,))
        store = DraftImageStorage(tmp_path)
        (tmp_path / "data/images").mkdir(parents=True)
        for pid in ("P001", "P002"):
            shutil.copyfile(ROOT / f"data/images/{pid}.jpg", tmp_path / f"data/images/{pid}.jpg")
        client.app.state.catalog_drafts.images = store
        yield client


def body(api, endpoint=ENDPOINT):
    draft = api.get(endpoint).json()["draft"]
    return {"version": draft["version"], "base_catalog_fingerprint": draft["base_catalog_fingerprint"], "product": draft["product"]}


def save(api, changes=None, endpoint=ENDPOINT):
    payload = body(api, endpoint)
    payload["product"].update(changes or {})
    response = api.post(endpoint, headers=H, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["draft"]


def provenance(api, pid="P001"):
    asset = api.app.state.services.products.asset_for_product(pid)
    return {k: asset[k] for k in ("source_page", "original_url", "download_url", "transformations", "author", "license", "license_url", "retrieved_at", "real_photo_review")}


def upload(api, version, pid="P001", metadata=None, extra=None):
    return api.post(ENDPOINT + "/image", headers=H, data={"version": str(version), "provenance": json.dumps(metadata or provenance(api, pid)), **(extra or {})},
                    files={"image": ("untrusted-name.jpg", (ROOT / f"data/images/{pid}.jpg").read_bytes(), "image/jpeg")})


def test_read_does_not_create_draft_and_save_isolated_from_live(api):
    before = api.get("/api/v1/products/P001").json()["product"]
    index = api.app.state.services.index.fingerprint
    assert api.get(ENDPOINT).json()["draft"]["has_draft"] is False
    assert api.app.state.catalog_drafts.repository.all() == []
    draft = save(api, {"name": "Tên sản phẩm đang soạn", "price_vnd": 123456})
    assert draft["version"] == 1 and draft["published"] is False and draft["has_draft"]
    assert "local_path" not in json.dumps(draft) and "image_path" not in json.dumps(draft)
    assert api.get("/api/v1/products/P001").json()["product"] == before
    assert api.app.state.purchases.catalog()["P001"]["price_vnd"] == before["price_vnd"]
    assert api.app.state.services.index.fingerprint == index
    assert api.get("/api/v1/admin/products?status=draft").json()["total"] == 1


def test_cas_discard_tombstone_recreate_and_base_conflicts(api):
    original = body(api)
    draft = save(api)
    assert api.post(ENDPOINT, headers=H, json=original).json()["error"]["code"] == "DRAFT_CHANGED"
    result = api.post(ENDPOINT + "/discard", headers=H, json={"version": draft["version"]})
    assert result.json()["draft"]["has_draft"] is False and result.json()["draft"]["version"] == 2
    assert save(api)["version"] == 3
    assert api.post(ENDPOINT, headers=H, json={**original, "version": 1}).status_code == 409
    assert api.post(ENDPOINT, headers=H, json={**body(api), "base_catalog_fingerprint": "f" * 64}).json()["error"]["code"] == "CATALOG_CHANGED"


def test_concurrent_writes_one_winner_and_audit_rollback(api):
    service = api.app.state.catalog_drafts
    payload = body(api)
    def operation(name):
        try:
            service.save(api.actor, "P001", DraftSave.model_validate({**payload, "product": {**payload["product"], "name": name}}), 0)
            return True
        except AppError as error:
            assert error.code == "DRAFT_CHANGED"
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(operation, ["First edit", "Second edit"])) == 1
    before = api.get(ENDPOINT).json()["draft"]
    with service.repository.accounts.connection() as db:
        db.execute("CREATE TRIGGER fail_draft BEFORE INSERT ON admin_audit WHEN NEW.action LIKE 'catalog.draft.%' BEGIN SELECT RAISE(ABORT,'test failure'); END")
    assert api.post(ENDPOINT, headers=H, json=body(api)).status_code == 500
    assert api.get(ENDPOINT).json()["draft"] == before


def test_upload_preserves_bytes_provenance_preview_and_detects_corruption(api):
    draft = save(api)
    result = upload(api, draft["version"])
    assert result.status_code == 200, result.text
    draft = result.json()["draft"]
    assert draft["version"] == 2 and draft["image"]["sha256"] == provenance_asset(api)["sha256"]
    assert api.get(draft["image_url"]).content == (ROOT / "data/images/P001.jpg").read_bytes()
    assert api.get(ENDPOINT + "/image?v=1").status_code == 409
    record = api.app.state.catalog_drafts.repository.get("P001")
    path, raw = api.app.state.catalog_drafts.images.read(record["asset"])
    path.write_bytes(raw + b"tampered")
    assert api.get(ENDPOINT + "/image").json()["error"]["code"] == "DRAFT_IMAGE_UNAVAILABLE"


def provenance_asset(api):
    return api.app.state.services.products.asset_for_product("P001")


def test_duplicate_catalog_photo_and_invalid_upload_do_not_mutate_draft(api):
    draft = save(api)
    assert upload(api, draft["version"], "P002").json()["error"]["code"] == "IMAGE_ALREADY_USED"
    for changes in [{"real_photo_review": "pending"}, {"source_page": "javascript:alert(1)"}, {"license_url": "https://user:password@example.test"}, {"author": " "}, {"retrieved_at": 0}, {"retrieved_at": "2999-01-01"}]:
        metadata = {**provenance(api), **changes}
        assert upload(api, draft["version"], metadata=metadata).status_code == 422
    assert upload(api, draft["version"], extra={"customer_id": "C001"}).status_code == 422
    invalid = api.post(ENDPOINT + "/image", headers=H, data={"version": "1", "provenance": json.dumps(provenance(api))}, files={"image": ("a.jpg", b"not an image", "image/jpeg")})
    assert invalid.status_code == 415
    assert api.get(ENDPOINT).json()["draft"] == draft


class EncoderDouble:
    available = True
    model_fingerprint = "d" * 64
    calls = 0

    def validate_text(self, text):
        return text

    def encode_texts(self, texts):
        self.calls += 1
        return np.ones((1, 512), np.float32)

    def encode_images(self, images):
        self.calls += 1
        return np.ones((1, 512), np.float32)


def test_preflight_requires_actual_capability_and_invalidates_after_edit(api):
    save(api)
    assert api.post(ENDPOINT + "/preflight", headers=H, json={"version": 1}).json()["error"]["code"] == "MODEL_UNAVAILABLE"
    encoder = EncoderDouble()
    api.app.state.catalog_drafts.encoder = encoder
    response = api.post(ENDPOINT + "/preflight", headers=H, json={"version": 1})
    assert response.status_code == 200, response.text
    draft = response.json()["draft"]
    assert draft["validation"]["checked_version"] == 1 and draft["version"] == 2
    assert encoder.calls == 2 and draft["validation"]["published"] is False
    assert save(api, {"price_vnd": 345678})["validation"] is None
    assert api.post(ENDPOINT + "/preflight", headers=H, json={"version": 1}).status_code == 409
    assert encoder.calls == 2


def test_timed_out_preflight_cannot_commit_late_validation(api):
    save(api)
    completed = threading.Event()
    class SlowEncoder(EncoderDouble):
        def encode_texts(self, texts):
            time.sleep(0.1)
            return super().encode_texts(texts)

        def encode_images(self, images):
            completed.set()
            return super().encode_images(images)
    api.app.state.catalog_drafts.encoder = SlowEncoder()
    api.app.state.services.settings.search_timeout = 0.02
    response = api.post(ENDPOINT + "/preflight", headers=H, json={"version": 1})
    assert response.status_code == 504
    assert completed.wait(2)
    assert api.get(ENDPOINT).json()["draft"]["validation"] is None
    assert api.get(ENDPOINT).json()["draft"]["version"] == 1


def test_new_draft_creation_listing_discard_and_missing_image(api):
    endpoint = "/api/v1/admin/products/P981/draft"
    template = body(api, endpoint)
    assert template["product"] is None
    payload = {**template, "product": body(api)["product"]}
    assert api.post(endpoint, headers=H, json=payload).status_code == 200
    detail = api.get(endpoint).json()["draft"]
    assert detail["is_new"] and detail["image"] is None
    assert api.get("/api/v1/products/P981").status_code == 404
    assert api.post(endpoint + "/preflight", headers=H, json={"version": 1}).json()["error"]["code"] == "DRAFT_IMAGE_REQUIRED"
    assert api.get("/api/v1/admin/products?q=P981&status=draft&limit=1").json()["total"] == 1
    assert api.post(endpoint + "/discard", headers=H, json={"version": 1}).status_code == 200
    assert api.get("/api/v1/admin/products?q=P981").json()["total"] == 0


@pytest.mark.parametrize("changes", [{"price_vnd": True}, {"price_vnd": -1}, {"price_vnd": 1.5}, {"name": " "}, {"description": "x" * 501}, {"brand": "x\x00y"}, {"role": "admin"}, {"category": "unknown"}])
def test_strict_metadata(api, changes):
    payload = body(api)
    payload["product"].update(changes)
    assert api.post(ENDPOINT, headers=H, json=payload).status_code == 422
    assert api.app.state.catalog_drafts.repository.all() == []


def test_security_epoch_and_private_image(api):
    payload = body(api)
    save(api)
    with api.app.state.accounts.repository.connection() as db:
        api.app.state.accounts.repository.invalidate_sessions(db, api.actor)
    called = []
    with pytest.raises(AppError):
        api.app.state.catalog_drafts.repository.change(api.actor, "P001", 1, payload["base_catalog_fingerprint"], "image", lambda: called.append(True), expected_epoch=0)
    assert called == []
    assert api.get(ENDPOINT + "/image").status_code == 401
    assert api.post(ENDPOINT, headers=H, json=payload).status_code == 401
    api.post("/api/v1/auth/register", headers=AUTH, json={"email": "ordinary@example.test", "password": "ordinary passphrase test 2026", "display_name": "User"})
    assert api.get(ENDPOINT).status_code == 403
    assert api.get(ENDPOINT + "/image").status_code == 403
    assert api.post(ENDPOINT, headers=H, json=payload).status_code == 403


def test_restart_persistence_and_strict_query_contract(api):
    draft = save(api)
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=api.app.state.accounts.repository.path))) as fresh:
        assert fresh.app.state.catalog_drafts.repository.get("P001")["payload"] == draft["product"]
    for query in ["offset=-1", "limit=0", "limit=1&limit=2", "status=published", "customer_id=C001", "q=" + "a" * 121]:
        assert api.get("/api/v1/admin/products?" + query).status_code == 422
    assert api.post(ENDPOINT, json=body(api)).status_code == 403
    assert api.get(ENDPOINT + "?version=1").status_code == 422


def test_storage_refuses_paths_outside_workspace(api):
    storage = api.app.state.catalog_drafts.images
    with pytest.raises(AppError):
        storage.read({"local_path": "../not-allowed.jpg", "sha256": "a" * 64, "bytes": 1})


def test_new_real_photo_and_duplicate_between_drafts(api):
    source = json.loads((ROOT / "data/authoring/P181-source.json").read_text(encoding="utf-8"))
    metadata = {k: source[k] for k in provenance(api)}
    product = {"name": "Áo polo Nike trắng viền đỏ rượu", "brand": "Nike", "category": "t_shirt", "color": "trắng, đỏ rượu, xám", "price_vnd": 890000, "description": "Ảnh nghiêng áo polo trắng, cổ đỏ rượu và vai xám; tay áo có chữ ASB BANK."}
    for pid in ("P181", "P182"):
        endpoint = f"/api/v1/admin/products/{pid}/draft"
        initial = body(api, endpoint)
        assert api.post(endpoint, headers=H, json={**initial, "product": product}).status_code == 200
        result = api.post(endpoint + "/image", headers=H, data={"version": "1", "provenance": json.dumps(metadata)},
                          files={"image": ("../../do-not-use-filename.jpg", (ROOT / "data/authoring/P181.jpg").read_bytes(), "image/jpeg")})
        assert result.status_code == (200 if pid == "P181" else 409)
        if pid == "P181":
            assert result.json()["draft"]["image"]["download_url"] == source["download_url"]
            assert result.json()["draft"]["image"]["transformations"] == source["transformations"]
        else:
            assert result.json()["error"]["code"] == "IMAGE_ALREADY_USED"


def test_preflight_rejects_wrong_encoder_batch_without_recording(api):
    save(api)
    class BadEncoder(EncoderDouble):
        def encode_images(self, images):
            return np.ones(512, np.float32)
    api.app.state.catalog_drafts.encoder = BadEncoder()
    response = api.post(ENDPOINT + "/preflight", headers=H, json={"version": 1})
    assert response.status_code == 500 and response.json()["error"]["code"] == "INVALID_VECTOR"
    assert api.get(ENDPOINT).json()["draft"]["validation"] is None


def test_openapi_authoring_contract(api):
    paths = api.get("/openapi.json").json()["paths"]
    assert {p["name"] for p in paths["/api/v1/admin/products"]["get"]["parameters"]} == {"q", "status", "offset", "limit"}
    schema = paths["/api/v1/admin/products/{product_id}/draft/image"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]
    assert set(schema["required"]) == {"image", "version", "provenance"}
