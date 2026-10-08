"""HTTP integration with an explicitly labeled encoder double; no AI-quality claims."""

import io
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.application.query_service import QueryService
from app.application.search_service import SearchService
from app.data.vector_index import VectorIndex, build_index, unit
from app.main import Container, create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


class EncoderDouble:
    available = True
    model_fingerprint = "d" * 64

    def __init__(self):
        self.calls = 0

    def validate_text(self, text):
        return text

    def encode_texts(self, texts):
        self.calls += 1
        vector = unit(np.ones(512, dtype=np.float32))
        return np.repeat(vector[None, :], len(texts), axis=0)

    def encode_images(self, images):
        self.calls += 1
        vector = np.zeros(512, dtype=np.float32)
        vector[0] = 1
        return np.repeat(vector[None, :], len(images), axis=0)


@pytest.fixture
def api(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    settings = Settings(root=tmp_path, load_models=False)
    container = Container(settings)
    encoder = EncoderDouble()
    build_index(tmp_path, container.products, encoder)
    container.encoder = encoder
    container.index = VectorIndex(tmp_path, container.products.products, encoder.model_fingerprint)
    container.queries = QueryService(encoder)
    container.search = SearchService(container.products, encoder, container.index, tmp_path)
    encoder.calls = 0
    with TestClient(create_app(settings, container)) as client:
        yield client, encoder


def upload():
    buffer = io.BytesIO()
    Image.new("RGB", (7, 8), "red").save(buffer, format="PNG")
    return {"image": ("query.png", buffer.getvalue(), "image/png")}


def assert_search(response, mode):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["query"]["mode"] == mode
    assert body["results"]
    assert [r["rank"] for r in body["results"]] == list(range(1, len(body["results"]) + 1))
    assert body["meta"]["trace"][-1]["output_count"] == len(body["results"])
    assert all(-1 <= r["score"] <= 1 for r in body["results"])
    assert body["meta"]["model_fingerprint"] == "d" * 64
    assert response.headers["x-request-id"] == body["request_id"]
    assert "vector" not in body["query"]
    return body


def test_text_and_voice_share_search_results(api):
    client, encoder = api
    text = assert_search(client.post("/api/v1/search", json={"mode": "text", "text": "  giày   đỏ "}), "text")
    voice = assert_search(
        client.post("/api/v1/search", json={"mode": "voice", "text": "giày đỏ", "voice_source": "manual_transcript"}),
        "voice",
    )
    assert text["query"]["text"] == "giày đỏ"
    assert voice["query"]["voice_source"] == "manual_transcript"
    assert text["results"] == voice["results"]
    assert encoder.calls == 2
    assert client.get("/health/ready").status_code == 200


def test_image_and_multimodal_real_decoding_and_component_fields(api):
    client, _ = api
    image = assert_search(client.post("/api/v1/search/image", files=upload()), "image")
    assert image["query"]["image_summary"]["width"] == 7
    assert image["query"]["image_summary"]["height"] == 8
    assert image["query"]["text"] is None
    assert image["results"][0]["component_scores"]["text"] is None
    assert image["results"][0]["score"] == image["results"][0]["component_scores"]["image"]
    multi = assert_search(
        client.post("/api/v1/search/multimodal", files=upload(), data={"text": "giày đỏ", "text_weight": "0.3"}),
        "multimodal",
    )
    assert multi["query"]["text_weight"] == 0.3
    assert multi["results"][0]["component_scores"]["text"] is not None
    assert multi["results"][0]["component_scores"]["image"] is not None


def test_hard_filters_and_empty_response(api):
    client, _ = api
    options = {"top_k": 20, "filters": {"category": "bag", "in_stock": True, "max_price": 1500000}}
    body = assert_search(
        client.post("/api/v1/search/image", files=upload(), data={"options": json.dumps(options)}), "image"
    )
    assert [r["product"]["product_id"] for r in body["results"]] == ["P011"]
    empty = client.post(
        "/api/v1/search", json={"mode": "text", "text": "giày", "options": {"filters": {"max_price": 1}}}
    )
    assert empty.status_code == 200
    assert empty.json()["results"] == []
    assert empty.json()["meta"]["empty_reason"] == "filters"


@pytest.mark.parametrize(
    "blob,mime,status",
    [(b"not image", "image/png", 415), (b"\x89PNG\r\n\x1a\n", "image/png", 422), (b"GIF89a", "image/gif", 415)],
)
def test_invalid_upload_rejected_before_encoder(api, blob, mime, status):
    client, encoder = api
    response = client.post("/api/v1/search/image", files={"image": ("bad.png", blob, mime)})
    assert response.status_code == status
    assert encoder.calls == 0
    assert "error" in response.json() and "results" not in response.json()


@pytest.mark.parametrize(
    "data,status",
    [
        ({"options": '{"top_k":1,"top_k":2}'}, 400),
        ({"options": '{"top_k":true}'}, 422),
        ({"options": '{"top_k":21}'}, 422),
        ({"options": '{"unknown":1}'}, 422),
        ({"unknown": "bad"}, 422),
    ],
)
def test_multipart_options_validation(api, data, status):
    client, encoder = api
    response = client.post("/api/v1/search/image", files=upload(), data=data)
    assert response.status_code == status
    assert encoder.calls == 0


@pytest.mark.parametrize(
    "data,status",
    [
        ({}, 422),
        ({"text": "giày", "text_weight": "true"}, 422),
        ({"text": "giày", "text_weight": "NaN"}, 422),
        ({"text": "giày", "text_weight": "1"}, 422),
        ({"text": "   "}, 422),
        ({"text": "giày", "text_weight": '"0.5"'}, 422),
    ],
)
def test_multimodal_missing_text_or_bad_weight(api, data, status):
    client, encoder = api
    response = client.post("/api/v1/search/multimodal", files=upload(), data=data)
    assert response.status_code == status
    assert encoder.calls == 0


def test_relevant_missing_policy_is_explicit_and_nearest_still_works(api):
    client, _ = api
    response = client.post(
        "/api/v1/search", json={"mode": "text", "text": "giày", "options": {"result_policy": "relevant"}}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "RELEVANCE_POLICY_UNAVAILABLE"
    assert_search(client.post("/api/v1/search", json={"mode": "text", "text": "giày"}), "text")
