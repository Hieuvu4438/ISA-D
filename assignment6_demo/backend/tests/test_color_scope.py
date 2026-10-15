"""Explicit color intent must constrain retrieval independently of model scores."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.application.catalog_search import CatalogSearch
from app.application.query_service import Query
from app.application.search_service import SearchService
from app.domain import AppError, Filters, SearchOptions
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def catalog():
    rows = [dict(product_id=pid, name=f"Balo {color}", brand=brand, category=category,
                 color=color, description="Túi thời trang", price_vnd=price, stock_quantity=stock)
            for pid, color, brand, category, price, stock in [
                ("P001", "đỏ đậm và đen", "Nike", "backpack", 500000, 2),
                ("P002", "hồng và đen", "Nike", "backpack", 600000, 0),
                ("P003", "đen", "Adidas", "backpack", 700000, 3),
                ("P004", "xanh dương và trắng", "Nike", "backpack", 800000, 1),
                ("P005", "xanh lá", "Nike", "jacket", 900000, 2),
                ("P006", "đỏ", "Nike", "backpack", 400000, 4),
            ]]
    return CatalogSearch(SimpleNamespace(products=rows, fingerprint="color-fixture", summary=lambda p: dict(p)))


@pytest.mark.parametrize("text,ids", [
    ("balo màu đỏ", ["P001", "P006"]),
    ("BALO MAU DO", ["P001", "P006"]),
    ("balo ma\u0300u đo\u0309", ["P001", "P006"]),
    ("balo màu đỏ đậm", ["P001"]),
    ("balo color blue", ["P004"]),
    ("balo colour green", []),
    ("balo màu hồng hoặc đen", ["P001", "P002", "P003"]),
    ("balo màu hồng hoặc màu đỏ", ["P001", "P002", "P006"]),
    ("balo màu đỏ or blue", ["P001", "P004", "P006"]),
    ("Nike balo màu đen", ["P001", "P002"]),
    ("balo màu đỏ; dưới 450k", ["P006"]),
    ("balo màu đỏ; không màu đỏ đậm", ["P006"]),
    ("balo màu đỏ hoặc hồng; không màu đỏ", ["P002"]),
    ("balo màu đỏ P001", ["P001"]),
    ("balo màu đỏ P999", []),
])
def test_color_hard_scope_browse_suggestions_and_exact_ids(catalog, text, ids):
    result = catalog.browse(text, Filters(), "relevance", 0, 20)
    assert [p["product_id"] for p in result["products"]] == ids
    assert any(c["field"] == "color" for c in result["scope_interpretation"]["clauses"])
    assert [p["product_id"] for p in catalog.suggestions(text, 10)] == ids


@pytest.mark.parametrize("text", ["balo màu đỏ và đen", "balo màu đỏ, đen", "balo màu đỏ hoặc Nike", "balo màu ultraviolet", "balo màu", "balo màu đỏ hoặc"])
def test_ambiguous_unknown_and_incomplete_color_not_silently_forced(catalog, text):
    plan = catalog.scopes.interpret(text)
    assert plan.warnings
    assert not plan.clauses
    assert plan.lexical_text == text
    assert not catalog.scopes.interpret(text, False).warnings


@pytest.mark.parametrize("text,filters,code", [
    ("balo màu đỏ", Filters(color="đen"), "SCOPE_FILTER_CONFLICT"),
    ("balo màu đỏ; không màu đỏ", Filters(), "SCOPE_EXCLUSION_CONFLICT"),
    ("balo màu đỏ đậm; không màu đỏ", Filters(), "SCOPE_EXCLUSION_CONFLICT"),
    ("balo màu đỏ hoặc hồng; không màu đỏ và hồng", Filters(), "SCOPE_EXCLUSION_CONFLICT"),
])
def test_color_filter_and_exclusion_conflicts(catalog, text, filters, code):
    with pytest.raises(AppError) as error:
        catalog.browse(text, filters, "relevance", 0, 10)
    assert error.value.code == code


def test_manual_composite_filter_stock_facets_and_opt_out(catalog):
    assert catalog.browse("balo màu đỏ", Filters(color="đỏ đậm và đen"), "relevance", 0, 10)["total"] == 1
    result = catalog.browse("balo màu hồng hoặc đỏ", Filters(in_stock=True), "price_asc", 0, 1)
    assert result["total"] == 2
    assert result["products"][0]["product_id"] == "P006"
    assert next(c["count"] for c in result["facets"]["color"] if c["value"] == "hồng và đen") == 0
    assert not catalog.scopes.interpret("red shirt").clauses
    assert not catalog.scopes.interpret("màu đỏ", False).clauses


@pytest.mark.parametrize("mode,strategy", [("text", "semantic"), ("text", "hybrid"), ("voice", "hybrid"), ("multimodal", "hybrid")])
def test_wrong_color_high_cosine_cannot_beat_hard_constraint(catalog, tmp_path, mode, strategy):
    index = SimpleNamespace(available=True, fingerprint="a" * 64,
                            product_vectors=np.tile(np.eye(1, 512, dtype=np.float32), (len(catalog.products), 1)),
                            retrieve=lambda _: [{"row": i, "product_id": p["product_id"], "score": .5 if p["product_id"] == "P002" else .99} for i, p in enumerate(catalog.products)])
    service = SearchService(catalog.repository, SimpleNamespace(available=True, model_fingerprint="b" * 64), index, tmp_path)
    text = "balo màu hồng"
    options = SearchOptions(top_k=1, search_strategy=strategy)
    query = Query(mode, np.eye(1, 512)[0], None, None, options, {"text": text})
    service.validate_request(options, mode, text)
    result = service.search(query)
    assert [r["product"]["product_id"] for r in result["results"]] == ["P002"]
    assert result["query"]["text"] == text
    assert any(c["field"] == "color" for c in result["meta"]["scope_interpretation"]["clauses"])
    with pytest.raises(AppError) as error:
        service.validate_request(SearchOptions(filters=Filters(color="đen")), mode, text)
    assert error.value.code == "SCOPE_FILTER_CONFLICT"


def test_public_http_allows_color_intent_without_loading_encoder(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "accounts.sqlite3"))) as api:
        for endpoint in ["catalog", "suggestions"]:
            r = api.get(f"/api/v1/{endpoint}", params={"q": "balo màu hồng"})
            assert r.status_code == 200
            assert r.json()["products"]
            assert all("hồng" in p["color"] for p in r.json()["products"])
        r = api.get('/api/v1/catalog', params={"q": "balo màu hồng", "color": "đen"})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "SCOPE_FILTER_CONFLICT"
