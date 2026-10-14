from pathlib import Path
import math
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.application.catalog_search import CatalogSearch, analyze, fold, one_edit
from app.application.query_service import Query
from app.application.search_service import SearchService
from app.data.product_repository import ProductRepository
from app.domain import AppError, Filters, SearchOptions
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def catalog():
    return CatalogSearch(ProductRepository(ROOT))


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path_factory.mktemp("browse") / "accounts.sqlite3"))) as client:
        yield client


def test_accent_nfc_alias_and_bounded_typo(catalog):
    assert fold("GIÀY ĐỎ") == fold("gia\u0300y đo\u0309") == "giay do"
    variants = ["áo thun", "ao thun", "áo phông", "tshirt", "t-shirt"]
    results = [catalog.browse(query, Filters(), "relevance", 0, 100)["products"] for query in variants]
    assert all(rows == results[0] for rows in results)
    assert all(p["category"] == "t_shirt" for p in results[0])
    query = catalog.prepare("snekaer")
    assert query.corrections == [{"input": "snekaer", "matched": "sneaker"}]
    assert query.terms == ["cat_casual_shoes"]
    # Short Vietnamese terms, numeric SKU and ambiguous guesses never rewritten.
    assert catalog.prepare("gia p999 1234").corrections == []
    assert analyze("black t-shirt") == ["den", "cat_t_shirt"]
    assert analyze("giày chạy địa hình") == ["cat_trail_shoes"]


@pytest.mark.parametrize("a,b,result", [("abcd", "abdc", True), ("abcd", "abc", True), ("abc", "abcd", True), ("abcd", "abce", True), ("abcd", "acbd", True), ("abcd", "abef", False), ("abcd", "abcd", False), ("a", "abc", False)])
def test_one_edit(a, b, result):
    assert one_edit(a, b) == result


def test_exact_sku_missing_punctuation_and_empty(catalog):
    exact = catalog.browse(" p001 ", Filters(), "relevance", 0, 20)
    assert exact["retrieval"] == "exact_sku" and exact["total"] == 1
    assert exact["products"][0]["product_id"] == "P001"
    assert catalog.browse("P999", Filters(), "relevance", 0, 20)["empty_reason"] == "no_matches"
    assert catalog.browse("!!!", Filters(), "relevance", 0, 20)["total"] == 0
    assert catalog.browse("", Filters(), "relevance", 0, 20)["total"] == len(catalog.products)
    # Literal punctuation is never treated as SQL, regex or Lucene operators.
    assert isinstance(catalog.browse("' OR 1=1 --", Filters(), "relevance", 0, 20)["products"], list)


def test_filter_boundaries_facets_before_pagination_and_stable_sorts(catalog):
    product = catalog.products[0]
    filters = Filters(category=product["category"], brand=product["brand"], min_price=product["price_vnd"], max_price=product["price_vnd"], color=product["color"])
    page = catalog.browse("", filters, "price_asc", 0, 1)
    assert page["total"] >= 1 and page["products"][0]["price_vnd"] == product["price_vnd"]
    assert page["facets"] == catalog.browse("", filters, "price_asc", 0, 100)["facets"]
    # Relax only category; retain brand, price, color, stock when computing its counts.
    expected = [p for p in catalog.products if p["brand"] == product["brand"] and p["price_vnd"] == product["price_vnd"] and p["color"] == product["color"]]
    assert sum(row["count"] for row in page["facets"]["category"]) == len(expected)
    for sort in ("price_asc", "price_desc", "name", "relevance"):
        rows = catalog.browse("", Filters(), sort, 0, 100)["products"]
        assert rows == catalog.browse("", Filters(), sort, 0, 100)["products"]
        if sort.startswith("price"):
            prices = [p["price_vnd"] for p in rows]
            assert prices == sorted(prices, reverse=sort == "price_desc")
    ids = [p["product_id"] for p in catalog.browse("", Filters(), "relevance", 0, 100)["products"]]
    ids += [p["product_id"] for p in catalog.browse("", Filters(), "relevance", 100, 100)["products"]]
    assert len(ids) == len(set(ids)) == len(catalog.products)
    assert catalog.browse("", Filters(max_price=0), "relevance", 0, 24)["empty_reason"] == "filters"


def test_rrf_whole_eligible_set_cosine_untouched(catalog):
    candidates = [{"product_id": p["product_id"], "score": 0.8 - i * .001} for i, p in enumerate(catalog.products)]
    results, plan = catalog.fuse(candidates, "áo thun")
    assert len(results) == len(candidates)
    assert [p["score"] for p in results] == [p["score"] for p in candidates]
    first_lexical_id = max(catalog.scores(plan), key=catalog.scores(plan).get)
    index = next(i for i, row in enumerate(candidates) if row["product_id"] == first_lexical_id)
    fused = next(row for row in results if row["product_id"] == first_lexical_id)
    assert fused["rank_score"] == pytest.approx(1 / (60 + index + 1) + 1 / 61)
    assert all(math.isfinite(row["rank_score"]) for row in results)
    exact, _ = catalog.fuse(candidates, "P001")
    assert len(exact) == 1 and exact[0]["product_id"] == "P001"


def test_hybrid_threshold_then_fusion_top_k_and_price_sort(catalog, tmp_path):
    products = catalog.products[:3]
    # A deliberately adversarial index double, no AI quality claims.
    index = SimpleNamespace(available=True, fingerprint="a" * 64,
        product_vectors=np.tile(np.eye(1, 512, dtype=np.float32), (3, 1)),
        retrieve=lambda _: [{"row": i, "product_id": p["product_id"], "score": .3 + .1 * i} for i, p in enumerate(products)])
    encoder = SimpleNamespace(available=True, model_fingerprint="b" * 64)
    service = SearchService(catalog.repository, encoder, index, tmp_path)
    service._policies = [{"mode": "text", "threshold": .45}]
    query = Query("text", np.eye(1, 512)[0], None, None, SearchOptions(top_k=1, search_strategy="hybrid", result_policy="relevant"), {"text": "P001"})
    result = service.search(query)
    assert result["results"] == []  # Exact SKU cannot resurrect a below-threshold candidate.
    query.options = SearchOptions(top_k=2, search_strategy="hybrid", sort="price_asc")
    query.input_summary = {"text": "giày"}
    result = service.search(query)
    assert [r["product"]["price_vnd"] for r in result["results"]] == sorted(p["price_vnd"] for p in products)[:2]
    assert result["meta"]["ranking_strategy"] == "rrf"


def test_no_models_browse_suggestions_and_private_data(api):
    assert api.get("/health/ready").status_code == 503
    result = api.get("/api/v1/catalog?q=ao%20thun&sort=price_asc&limit=2")
    assert result.status_code == 200
    body = result.json()
    assert len(body["products"]) == 2 and body["total"] > 2
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-request-id"] == body["request_id"]
    assert "image_path" not in result.text and "stock_quantity" not in result.text
    suggestions = api.get("/api/v1/suggestions?q=P00&limit=3").json()["products"]
    assert [row["product_id"] for row in suggestions] == ["P001", "P002", "P003"]
    assert api.get("/api/v1/suggestions?q=a").json()["products"] == []
    assert api.get("/api/v1/catalog?offset=100000").json()["products"] == []


@pytest.mark.parametrize("query", ["q=a&q=b", "unknown=1", "category=bad", "category=", "brand=bad", "color=bad", "min_price=-1", "max_price=1.5", "min_price=2&max_price=1", "min_price=true", "in_stock=1", "in_stock=True", "offset=-1", "limit=0", "limit=101", "sort=random", "limit=1&limit=2", "q=" + "a" * 501, "q=" + "+".join(["a"] * 65)])
def test_strict_browse_input_validation(api, query):
    assert api.get("/api/v1/catalog?" + query).status_code == 422


def test_suggestions_limits_and_color_filter(api):
    assert api.get("/api/v1/suggestions?q=x&limit=11").status_code == 422
    assert api.get("/api/v1/suggestions?q=x&foo=1").status_code == 422
    detail = api.get("/api/v1/products/P001").json()["product"]
    body = api.get("/api/v1/catalog", params={"color": detail["color"], "in_stock": "true"}).json()
    assert all(row["color"] == detail["color"] and row["in_stock"] for row in body["products"])


def test_browse_openapi_parameters_match_public_wire_contract(api):
    schema = api.get("/openapi.json").json()
    parameters = {row["name"]: row["schema"] for row in schema["paths"]["/api/v1/catalog"]["get"]["parameters"]}
    assert set(parameters) == {"q", "limit", "offset", "sort", "category", "brand", "color", "min_price", "max_price", "in_stock"}
    assert parameters["limit"]["maximum"] == 100 and parameters["limit"]["default"] == 24
    assert parameters["sort"]["enum"] == ["relevance", "price_asc", "price_desc", "name"]
    suggestions = {row["name"]: row["schema"] for row in schema["paths"]["/api/v1/suggestions"]["get"]["parameters"]}
    assert suggestions["limit"]["maximum"] == 10


def test_prepare_invalid_long_and_zero_catalog(catalog):
    with pytest.raises(AppError):
        catalog.prepare("word " * 65)
    empty = CatalogSearch(SimpleNamespace(products=[], fingerprint="x", summary=lambda p: p))
    assert empty.browse("x", Filters(), "relevance", 0, 24)["empty_reason"] == "catalog_empty"
    assert empty.suggestions("shoe") == []
