"""Scope logic with adversarial doubles; real-model evidence is separate."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.application.catalog_search import CatalogSearch
from app.application.query_service import Query
from app.application.search_service import SearchService
from app.domain import AppError, Filters, SearchOptions
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def catalog():
    rows = [dict(product_id=pid, name=name, brand=brand, category=category, color=color, description=name,
                 price_vnd=price, stock_quantity=2) for pid, name, brand, category, color, price in [
        ("P001", "Áo thun Nike đỏ", "Nike", "t_shirt", "đỏ", 300000),
        ("P002", "Áo thun Adidas trắng", "Adidas", "t_shirt", "trắng", 500000),
        ("P003", "Áo khoác Nike đen", "Nike", "jacket", "đen", 700000),
        ("P004", "Giày New Balance", "New Balance", "running_shoes", "xanh", 900000),
        ("P005", "Áo thun Nike trắng", "Nike", "t_shirt", "trắng", 600000),
        ("P006", "Giày On", "On", "running_shoes", "xám", 1500000),
    ]]
    return CatalogSearch(SimpleNamespace(products=rows, fingerprint="scope-fixture", summary=lambda p: dict(p)))


@pytest.mark.parametrize("text,ids", [
    ("áo thun Nike", ["P001", "P005"]), ("NIKE A\u0301O THUN", ["P001", "P005"]),
    ("tôi muốn mua một chiếc áo thun Nike", ["P001", "P005"]),
    ("áo phông hãng Nike", ["P001", "P005"]), ("t-shirt Nike", ["P001", "P005"]),
    ("New Balance", ["P004"]), ("giày chạy bộ New Balance", ["P004"]),
    ("hãng On", ["P006"]), ("brand On", ["P006"]),
    ("áo thun Nike hoặc Adidas", ["P001", "P002", "P005"]),
    ("áo thun hoặc áo khoác Nike", ["P001", "P003", "P005"]),
    ("Nike Nike", ["P001", "P003", "P005"]),
    ("áo thun Nike P001", ["P001"]), ("áo thun Nike P999", []),
])
def test_exact_scope_intersection_union_and_sku(catalog, text, ids):
    result = catalog.browse(text, Filters(), "relevance", 0, 100)
    assert [p["product_id"] for p in result["products"]] == ids
    assert result["scope_interpretation"]["applied"]
    assert sum(row["count"] for row in result["facets"]["category"]) == len(ids)
    assert [p["product_id"] for p in catalog.suggestions(text, 10)] == ids


@pytest.mark.parametrize("text", ["Nike giống Adidas", "Nike vs Adidas", "Nike hoặc áo thun Adidas", "Nike hoặc áo thun", "Nike Adidas", "áo thun và áo khoác", "áo không tay Nike"])
def test_ambiguous_scope_remains_visible_and_unforced(catalog, text):
    plan = catalog.scopes.interpret(text)
    assert plan.warnings
    assert not plan.clauses
    assert plan.lexical_text == text
    assert not catalog.scopes.interpret(text, False).warnings


def test_explicit_scope_exclusion_and_manual_filter_conflicts(catalog):
    for text, filters, code in [
        ("áo thun Nike", Filters(brand="Adidas"), "SCOPE_FILTER_CONFLICT"),
        ("áo thun Nike", Filters(category="jacket"), "SCOPE_FILTER_CONFLICT"),
        ("áo thun Nike; trừ Nike", Filters(), "SCOPE_EXCLUSION_CONFLICT"),
        ("áo thun; trừ áo thun", Filters(), "SCOPE_EXCLUSION_CONFLICT"),
    ]:
        with pytest.raises(AppError) as error:
            catalog.browse(text, filters, "relevance", 0, 10)
        assert error.value.code == code
    result = catalog.browse("áo thun Nike hoặc Adidas; trừ Nike; dưới 600k", Filters(), "price_desc", 0, 10)
    assert [p["product_id"] for p in result["products"]] == ["P002"]
    assert catalog.browse("áo thun Nike", Filters(category="jacket"), "relevance", 0, 10, parse_scope=False)["products"][0]["product_id"] == "P003"


def test_short_preposition_brand_color_collision_and_metadata_case(catalog):
    assert not catalog.scopes.interpret("try on shoes").clauses
    rows = [dict(catalog.products[0], brand="Red"), dict(catalog.products[1], brand="red")]
    service = CatalogSearch(SimpleNamespace(products=rows, fingerprint="x", summary=lambda p: p))
    assert not service.scopes.interpret("red shirt").clauses
    assert len(service.scopes.interpret("brand RED").clauses) == 1
    assert service.browse("brand RED", Filters(), "relevance", 0, 10)["total"] == 2


@pytest.mark.parametrize("mode,strategy", [("text", "semantic"), ("text", "hybrid"), ("voice", "hybrid"), ("multimodal", "hybrid")])
def test_high_cosine_wrong_scope_cannot_win(catalog, tmp_path, mode, strategy):
    products = catalog.products
    index = SimpleNamespace(available=True, fingerprint="a" * 64, product_vectors=np.tile(np.eye(1, 512, dtype=np.float32), (len(products), 1)),
                            retrieve=lambda _: [{"row": i, "product_id": p["product_id"], "score": .5 if p["product_id"] == "P005" else .99} for i, p in enumerate(products)])
    service = SearchService(catalog.repository, SimpleNamespace(available=True, model_fingerprint="b" * 64), index, tmp_path)
    text = "áo thun Nike; không màu đỏ; dưới 700k"
    options = SearchOptions(top_k=1, search_strategy=strategy)
    query = Query(mode, np.eye(1, 512)[0], None, None, options, {"text": text})
    service.validate_request(options, mode, text)
    result = service.search(query)
    assert [r["product"]["product_id"] for r in result["results"]] == ["P005"]
    assert result["query"]["text"] == text
    assert {c["field"] for c in result["meta"]["scope_interpretation"]["clauses"]} == {"brand", "category"}
    query.options.interpret_scope = False
    assert service.search(query)["results"][0]["product"]["product_id"] == "P002"


def test_scope_strict_options_http_no_model_and_image_only(catalog, tmp_path):
    with pytest.raises(ValidationError):
        SearchOptions(interpret_scope="false")
    with pytest.raises(AppError):
        catalog.scopes.interpret("x" * 501)
    assert not catalog.scopes.interpret(None).clauses
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "accounts.sqlite3"))) as api:
        for endpoint in ("catalog", "suggestions"):
            assert api.get(f"/api/v1/{endpoint}?interpret_scope=1").status_code == 422
            assert api.get(f"/api/v1/{endpoint}?interpret_scope=false&interpret_scope=true").status_code == 422
            response = api.get(f"/api/v1/{endpoint}", params={"q": "giày chạy bộ Nike", "interpret_scope": "true"})
            assert response.status_code == 200
            assert response.json()["products"]
            assert all(p["brand"] == "Nike" and p["category"] == "running_shoes" for p in response.json()["products"])
        assert api.get("/openapi.json").json()["components"]["schemas"]["SearchOptions"]["properties"]["interpret_scope"]["default"] is True
