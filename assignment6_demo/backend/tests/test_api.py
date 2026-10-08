from pathlib import Path
import json

from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.settings import Settings


ROOT = Path(__file__).resolve().parents[2]


def client():
    return TestClient(create_app(Settings(root=ROOT, load_models=False)))


def test_catalog_orders_and_credits_work_without_models():
    with client() as api:
        assert api.get("/health/live").status_code == 200
        assert api.get("/health/ready").status_code == 503
        products = api.get("/api/v1/products").json()
        catalog_size = len(json.loads((ROOT / "data/products.json").read_text(encoding="utf-8")))
        assert products["total"] == catalog_size
        assert len(products["products"]) == min(12, catalog_size)
        assert products["products"][0]["product_id"] == "P001"
        detail = api.get("/api/v1/products/P001").json()["product"]
        assert detail["image_credit"]["license_url"].startswith("https://")
        assert api.get("/api/v1/media/products/P001").headers["content-type"] == "image/jpeg"
        assert len(api.get("/api/v1/credits").json()["credits"]) == catalog_size
        assert api.get("/api/v1/orders?order_id=O001").status_code == 200
        own = api.get("/api/v1/orders/O001").json()["order"]
        assert own["total_vnd"] == sum(i["line_total_vnd"] for i in own["items"])
        assert "customer_id" not in own
        foreign = api.get("/api/v1/orders/O002")
        missing = api.get("/api/v1/orders/O999")
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json()["error"]["code"] == missing.json()["error"]["code"]
        assert foreign.json()["error"]["message"] == missing.json()["error"]["message"]


def test_validation_errors_are_sanitized_and_customer_cannot_override():
    with client() as api:
        for body in [
            {"mode": "text", "text": "   "},
            {"mode": "text", "text": "giày", "options": {"top_k": True}},
            {"mode": "voice", "text": "giày"},
            {"mode": "text", "text": "giày", "voice_source": None},
            {"mode": "text", "text": "giày", "customer_id": "C002"},
        ]:
            response = api.post("/api/v1/search", json=body)
            assert response.status_code == 422
            assert "error" in response.json()
        response = api.post(
            "/api/v1/search",
            content='{"mode":"text","text":"a","text":"b"}',
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400
        assert api.get("/api/v1/orders/O002", headers={"X-Customer-ID": "C002"}).status_code == 422
        assert api.get("/api/v1/orders?order_id=O001&customer_id=C002").status_code == 422
        assert api.get("/api/v1/products?limit=1.5").status_code == 422


def test_unavailable_search_and_speech_do_not_fake_results():
    with client() as api:
        response = api.post("/api/v1/search", json={"mode": "text", "text": "giày chạy bộ màu đen"})
        assert response.status_code == 503
        assert "results" not in response.json()
        invalid = api.post("/api/v1/speech/transcriptions", files={"audio": ("bad.wav", b"not audio", "audio/wav")})
        assert invalid.status_code in (415, 422)
        assert api.get("/api/v1/meta").json()["speech"]["configuration_state"] == "unconfigured"


def test_media_condition_and_error_request_headers():
    with client() as api:
        response = api.get("/api/v1/media/products/P001")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert (
            api.get("/api/v1/media/products/P001", headers={"if-none-match": response.headers["etag"]}).status_code
            == 304
        )
        missing = api.get("/not-a-route")
        assert missing.status_code == 404
        assert missing.headers["x-request-id"] == missing.json()["error"]["request_id"]
        assert missing.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "body",
    [
        '{"mode":"text","text":"\\ud800"}',
        '{"mode":"text","text":"giày","options":{"top_k":1e999}}',
        '{"mode":"text","text":"giày","options":{"filters":{"brand":"\\udfff"}}}',
    ],
)
def test_invalid_unicode_and_overflow_json_rejected_before_models(body):
    with client() as api:
        response = api.post(
            "/api/v1/search", content=body.encode("utf-8"), headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_JSON"
        assert api.get("/health/live").status_code == 200
