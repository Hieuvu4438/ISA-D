from pathlib import Path
import io
import json
import numpy as np
import pytest
from PIL import Image

from app.application.image_service import ImageService
from app.application.query_service import QueryService
from app.application.search_service import SearchService
from app.data.product_repository import ProductRepository
from app.data.product_repository import digest
from app.data.vector_index import VectorIndex, build_index, unit
from app.domain import AppError, SearchOptions

ROOT = Path(__file__).resolve().parents[2]


class EncoderDouble:
    available = True
    model_fingerprint = "a" * 64

    def validate_text(self, text):
        return text

    def encode_texts(self, texts):
        return np.repeat(unit(np.ones(512, dtype=np.float32))[None, :], len(texts), axis=0)

    def encode_images(self, images):
        v = np.zeros(512, dtype=np.float32)
        v[0] = 1
        return np.repeat(v[None, :], len(images), axis=0)


def image_bytes():
    stream = io.BytesIO()
    Image.new("RGBA", (8, 9), (255, 0, 0, 128)).save(stream, format="PNG")
    return stream.getvalue()


def test_real_image_decoder_validation():
    decoded, summary = ImageService.decode(image_bytes(), "image/png")
    assert decoded.mode == "RGB" and decoded.size == (8, 9)
    assert summary["format"] == "PNG"
    with pytest.raises(AppError):
        ImageService.decode(b"not an image")
    with pytest.raises(AppError):
        ImageService.decode(image_bytes(), "image/jpeg")


@pytest.mark.parametrize("value", [np.zeros(512), np.full(512, np.nan), np.ones(511)])
def test_unit_rejects_invalid_vectors(value):
    with pytest.raises(AppError):
        unit(value)


def test_full_search_fusion_filter_ties_and_policy(tmp_path):
    repo = ProductRepository(ROOT)
    encoder = EncoderDouble()
    meta = build_index(tmp_path, repo, encoder)
    index = VectorIndex(tmp_path, repo.products, encoder.model_fingerprint)
    assert index.available and index.fingerprint == meta["fingerprint"]
    service = SearchService(repo, encoder, index, tmp_path)
    options = SearchOptions(top_k=20, filters={"in_stock": True, "min_price": 1600000})
    query = QueryService(encoder).build_multimodal("  giày   đỏ ", image_bytes(), options, 0.5)
    result = service.search(query)
    ids = [r["product"]["product_id"] for r in result["results"]]
    assert ids == sorted(ids)
    assert "P009" not in ids and "P012" not in ids
    assert all(r["product"]["price_vnd"] >= 1600000 for r in result["results"])
    row = result["results"][0]
    c = row["component_scores"]
    fusion_norm = np.linalg.norm(0.5 * query.text_vector + 0.5 * query.image_vector)
    assert row["score"] == pytest.approx((0.5 * c["text"] + 0.5 * c["image"]) / fusion_norm)
    assert result["meta"]["trace"][-1]["output_count"] == len(ids)
    query.options = SearchOptions(result_policy="relevant")
    with pytest.raises(AppError) as error:
        service.search(query)
    assert error.value.code == "RELEVANCE_POLICY_UNAVAILABLE"


def test_index_detects_stale_metadata(tmp_path):
    repo = ProductRepository(ROOT)
    encoder = EncoderDouble()
    build_index(tmp_path, repo, encoder)
    products = repo.products
    products[0]["price_vnd"] += 1
    index = VectorIndex(tmp_path, products, encoder.model_fingerprint)
    assert not index.available and index.error_code == "INDEX_STALE"


def test_matching_policy_relevant_empty_and_custom_weight_unavailable(tmp_path):
    repo = ProductRepository(ROOT)
    encoder = EncoderDouble()
    meta = build_index(tmp_path, repo, encoder)
    index = VectorIndex(tmp_path, repo.products, encoder.model_fingerprint)
    policy = {
        "schema_version": 1,
        "index_fingerprint": meta["fingerprint"],
        "model_fingerprint": encoder.model_fingerprint,
        "scoring_version": "cosine_fusion_v1",
        "policies": [
            {"mode": "text", "text_weight": None, "threshold": 1.0},
            {"mode": "multimodal", "text_weight": 0.5, "threshold": -1.0},
        ],
    }
    policy["fingerprint"] = digest(policy)
    directory = tmp_path / "runtime/policies"
    directory.mkdir()
    (directory / f"relevance_{index.fingerprint}.json").write_text(json.dumps(policy), encoding="utf-8")
    service = SearchService(repo, encoder, index, tmp_path)
    qs = QueryService(encoder)
    options = SearchOptions(result_policy="relevant")
    text = service.search(qs.build_text("voice", "giày", options, "manual_transcript"))
    assert text["results"] == [] and text["meta"]["empty_reason"] == "threshold"
    assert text["meta"]["policy_fingerprint"] == policy["fingerprint"]
    multi = service.search(qs.build_multimodal("giày", image_bytes(), options, 0.5))
    assert multi["results"]
    with pytest.raises(AppError):
        service.search(qs.build_multimodal("giày", image_bytes(), options, 0.6))


def test_empty_filters_not_confused_with_dependency_error(tmp_path):
    repo = ProductRepository(ROOT)
    encoder = EncoderDouble()
    build_index(tmp_path, repo, encoder)
    index = VectorIndex(tmp_path, repo.products, encoder.model_fingerprint)
    service = SearchService(repo, encoder, index, tmp_path)
    query = QueryService(encoder).build_text("text", "giày", SearchOptions(filters={"max_price": 1}))
    result = service.search(query)
    assert result["results"] == [] and result["meta"]["empty_reason"] == "filters"
    index.available = False
    index.error_code = "INDEX_CORRUPT"
    with pytest.raises(AppError) as error:
        service.search(query)
    assert error.value.code == "INDEX_CORRUPT"


def test_npz_corruption_is_rejected(tmp_path):
    repo = ProductRepository(ROOT)
    encoder = EncoderDouble()
    meta = build_index(tmp_path, repo, encoder)
    path = tmp_path / f"runtime/index/vectors_{meta['fingerprint']}.npz"
    path.write_bytes(b"corrupt archive")
    index = VectorIndex(tmp_path, repo.products, encoder.model_fingerprint)
    assert not index.available and index.error_code == "INDEX_CORRUPT"


def test_query_text_normalization_and_wrong_provenance():
    qs = QueryService(EncoderDouble())
    assert qs.build_text("text", "  gia\u0300y   đỏ ", SearchOptions()).input_summary["text"] == "giày đỏ"
    for mode, source in [("voice", None), ("text", "azure")]:
        with pytest.raises(AppError):
            qs.build_text(mode, "giày", SearchOptions(), source)


@pytest.mark.parametrize("weight", [True, float("nan"), float("inf"), 0.09, 0.91])
def test_multimodal_weight_validation(weight):
    with pytest.raises(AppError):
        QueryService(EncoderDouble()).build_multimodal("giày", image_bytes(), SearchOptions(), weight)


def test_image_dimensions_and_truncated_payload():
    stream = io.BytesIO()
    Image.new("RGB", (8193, 1)).save(stream, format="PNG")
    with pytest.raises(AppError) as error:
        ImageService.decode(stream.getvalue())
    assert error.value.code == "IMAGE_DIMENSIONS_EXCEEDED"
    with pytest.raises(AppError):
        ImageService.decode(image_bytes()[:30])
