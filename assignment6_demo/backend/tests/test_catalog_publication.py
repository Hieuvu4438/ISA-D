"""Publication transactions with real SQLite and explicit deterministic encoder double."""
import asyncio
import json
from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
import numpy as np
import pytest

from app.application.index_builder import build_index
from app.application.query_service import QueryService
from app.application.search_service import SearchService
from app.catalog_gate import CatalogGate
from app.data.vector_index import VectorIndex
from app.main import Container, create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
H = {"X-Cortis-Intent": "admin"}
SHOP = {"X-Cortis-Intent": "commerce"}


class EncoderDouble:
    available = True
    model_fingerprint = "d" * 64

    def __init__(self):
        self.rows = []

    def validate_text(self, text):
        return text

    def encode_texts(self, texts):
        self.rows.append(("text", len(texts)))
        return np.ones((len(texts), 512), np.float32)

    def encode_images(self, images):
        self.rows.append(("image", len(images)))
        return np.ones((len(images), 512), np.float32)


@pytest.fixture
def api(tmp_path):
    (tmp_path / "data/images").mkdir(parents=True)
    products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))[:2]
    manifest = json.loads((ROOT / "data/image_sources.json").read_text(encoding="utf-8"))
    manifest["assets"] = [a for a in manifest["assets"] if a["product_id"] in {"P001", "P002"}]
    for product in products:
        shutil.copyfile(ROOT / product["image_path"], tmp_path / product["image_path"])
    (tmp_path / "data/products.json").write_text(json.dumps(products), encoding="utf-8")
    (tmp_path / "data/image_sources.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "data/orders.json").write_text("[]", encoding="utf-8")
    settings = Settings(root=tmp_path, load_models=False)
    container = Container(settings)
    encoder = EncoderDouble()
    build_index(tmp_path, container.products, encoder)
    container.encoder = encoder
    container.index = VectorIndex(tmp_path, container.products.products, encoder.model_fingerprint)
    container.queries = QueryService(encoder)
    container.search = SearchService(container.products, encoder, container.index, tmp_path)
    encoder.rows.clear()
    with TestClient(create_app(settings, container)) as client:
        result = client.post("/api/v1/auth/register", headers={"X-Cortis-Intent": "account"}, json={"email": "publisher@example.test", "display_name": "Publisher", "password": "publication test passphrase 2026"})
        client.actor = result.json()["user"]["user_id"]
        with client.app.state.accounts.repository.connection() as db:
            db.execute("UPDATE accounts SET role='admin' WHERE user_id=?", (client.actor,))
        client.encoder = encoder
        client.settings = settings
        yield client


def save(api, pid="P001", updates=None):
    endpoint = f"/api/v1/admin/products/{pid}/draft"
    draft = api.get(endpoint).json()["draft"]
    metadata = draft["product"] or api.get("/api/v1/admin/products/P001/draft").json()["draft"]["product"]
    metadata.update(updates or {})
    response = api.post(endpoint, headers=H, json={"version": draft["version"], "base_catalog_fingerprint": draft["base_catalog_fingerprint"], "product": metadata})
    assert response.status_code == 200, response.text
    return response.json()["draft"]


def publish(api, draft):
    return api.post(f"/api/v1/admin/products/{draft['product_id']}/draft/publish", headers=H, json={"version": draft["version"]})


def test_update_publish_atomic_catalog_price_media_search_and_restart(api):
    before = api.get("/api/v1/meta").json()["index"]
    original = api.get("/api/v1/media/products/P001").content
    assert api.post("/api/v1/cart/items", headers=SHOP, json={"product_id": "P001", "quantity": 1, "version": 0}).status_code == 200
    quote = api.post("/api/v1/checkout/quote", headers=SHOP, json={}).json()["quote"]
    draft = save(api, updates={"name": "Giày thử xuất bản", "price_vnd": 777777})
    result = publish(api, draft)
    assert result.status_code == 200, result.text
    publication = result.json()["publication"]
    assert publication["published"] and publication["catalog_fingerprint"] != before["catalog_fingerprint"]
    assert publication["index_fingerprint"] != before["index_fingerprint"]
    assert api.encoder.rows == [("text", 1), ("image", 1)]
    product = api.get("/api/v1/products/P001").json()["product"]
    assert product["price_vnd"] == 777777 and product["name"] == "Giày thử xuất bản"
    assert api.get("/api/v1/media/products/P001").content == original
    assert api.get("/api/v1/cart").json()["cart"]["subtotal_vnd"] == 777777
    assert api.get("/api/v1/catalog?q=P001").json()["products"][0]["price_vnd"] == 777777
    search = api.post("/api/v1/search", json={"mode": "text", "text": "P001", "options": {"search_strategy": "hybrid"}})
    assert search.status_code == 200 and search.json()["results"][0]["product"]["price_vnd"] == 777777
    address = {"recipient": "Demo buyer", "phone": "0900000000", "address_line": "Test street", "city": "Test city"}
    stale = api.post("/api/v1/purchases", headers=SHOP, json={"quote_id": quote["quote_id"], "idempotency_key": str(uuid4()), "shipping_address": address})
    assert stale.json()["error"]["code"] == "PRICE_CHANGED"
    with TestClient(create_app(api.settings)) as restarted:
        assert restarted.get("/api/v1/products/P001").json()["product"]["price_vnd"] == 777777
        assert restarted.get("/api/v1/media/products/P001").content == original
    assert result.json()["draft"]["has_draft"] is False
    # Seed files were never modified.
    assert json.loads((api.settings.root / "data/products.json").read_text(encoding="utf-8"))[0]["price_vnd"] == 1800000


def test_new_photo_product_publication_default_stock_zero_and_second_edit(api):
    draft = save(api, "P181", {"name": "Áo polo Nike trắng viền đỏ", "brand": "Nike", "category": "t_shirt", "color": "trắng, đỏ rượu, xám", "price_vnd": 890000})
    source = json.loads((ROOT / "data/authoring/P181-source.json").read_text(encoding="utf-8"))
    keys = ("source_page", "original_url", "download_url", "transformations", "author", "license", "license_url", "retrieved_at", "real_photo_review")
    upload = api.post("/api/v1/admin/products/P181/draft/image", headers=H, data={"version": str(draft["version"]), "provenance": json.dumps({k: source[k] for k in keys})}, files={"image": ("photo.jpg", (ROOT / "data/authoring/P181.jpg").read_bytes(), "image/jpeg")})
    assert upload.status_code == 200
    response = publish(api, upload.json()["draft"])
    assert response.status_code == 200, response.text
    product = api.get("/api/v1/products/P181").json()["product"]
    assert product["stock_quantity"] == 0 and not product["in_stock"]
    assert product["image_credit"]["author"] == "Auckland Museum"
    assert api.get("/api/v1/media/products/P181").content == (ROOT / "data/authoring/P181.jpg").read_bytes()
    assert api.get("/api/v1/catalog?q=P181&in_stock=true").json()["total"] == 0
    draft = save(api, "P181", {"price_vnd": 910000})
    # Inherited published image is read from its release, not missing seed data/images/P181.jpg.
    preflight = api.post("/api/v1/admin/products/P181/draft/preflight", headers=H, json={"version": draft["version"]})
    assert preflight.status_code == 200, preflight.text
    assert publish(api, preflight.json()["draft"]).status_code == 200
    assert api.get("/api/v1/products/P181").json()["product"]["price_vnd"] == 910000


def test_audit_failure_or_changed_draft_cannot_activate(api):
    draft = save(api, updates={"price_vnd": 111111})
    before = api.get("/api/v1/meta").json()["index"]
    with api.app.state.accounts.repository.connection() as db:
        db.execute("CREATE TRIGGER fail_publish BEFORE INSERT ON admin_audit WHEN NEW.action='catalog.publish' BEGIN SELECT RAISE(ABORT,'test failure'); END")
    assert publish(api, draft).status_code == 500
    assert api.get("/api/v1/meta").json()["index"] == before
    assert api.app.state.catalog_drafts.repository.active() is None
    with api.app.state.accounts.repository.connection() as db:
        db.execute("DROP TRIGGER fail_publish")
    prepared = api.app.state.catalog_publication.prepare("P001", draft["version"])
    save(api, updates={"price_vnd": 222222})
    with pytest.raises(Exception, match="Bản nháp"):
        api.app.state.catalog_publication.activate(api.app, prepared, api.actor, 0)
    assert api.get("/api/v1/meta").json()["index"] == before


def test_other_drafts_rebase_but_require_reload_and_auth_rechecked(api):
    first = save(api, "P001", {"price_vnd": 111111})
    other = save(api, "P002", {"price_vnd": 222222})
    assert publish(api, first).status_code == 200
    assert publish(api, other).status_code == 409
    current = api.get("/api/v1/admin/products/P002/draft").json()["draft"]
    assert current["product"]["price_vnd"] == 222222 and current["version"] == other["version"] + 1
    prepared = api.app.state.catalog_publication.prepare("P002", current["version"])
    with api.app.state.accounts.repository.connection() as db:
        api.app.state.accounts.repository.invalidate_sessions(db, api.actor)
    with pytest.raises(Exception):
        api.app.state.catalog_publication.activate(api.app, prepared, api.actor, 0)
    assert api.app.state.catalog_drafts.products.get_by_id("P002")["price_vnd"] != 222222


def test_catalog_gate_waits_for_readers_and_resumes_after_writer():
    async def run():
        gate = CatalogGate()
        entered = asyncio.Event()
        release = asyncio.Event()
        events = []
        async def read():
            async with gate.read():
                events.append("read")
                entered.set()
                await release.wait()
        async def write():
            async with gate.write():
                events.append("write")
        task = asyncio.create_task(read())
        await entered.wait()
        writer = asyncio.create_task(write())
        await asyncio.sleep(0)
        assert events == ["read"]
        release.set()
        await asyncio.gather(task, writer)
        async with gate.read():
            events.append("read_after")
        assert events == ["read", "write", "read_after"]
    asyncio.run(run())


def test_category_change_with_existing_sizes_is_rejected(api):
    revision = api.app.state.purchases.repository.snapshot()[1]
    allocated = api.post("/api/v1/admin/products/P001/variants", headers=H, json={"size": "40", "quantity": 1, "revision": revision, "reason": "Demo size assignment"})
    assert allocated.status_code == 201
    draft = save(api, updates={"category": "t_shirt"})
    before = api.get("/api/v1/meta").json()["index"]
    result = publish(api, draft)
    assert result.status_code == 409 and result.json()["error"]["code"] == "CATEGORY_HAS_VARIANTS"
    assert api.get("/api/v1/meta").json()["index"] == before


def test_model_failure_never_changes_active_catalog(api):
    draft = save(api, updates={"price_vnd": 123456})
    before = api.get("/api/v1/products/P001").json()["product"]
    api.encoder.available = False
    result = publish(api, draft)
    assert result.status_code == 503 and result.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert api.get("/api/v1/products/P001").json()["product"] == before
    assert api.app.state.catalog_drafts.repository.active() is None
