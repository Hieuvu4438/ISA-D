"""Adversarial logic tests; deterministic index double is not AI quality evidence."""
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
    rows = [
        {"product_id": "P001", "name": "Áo Nike đỏ", "brand": "Nike", "category": "t_shirt", "color": "đỏ", "description": "Áo thun", "price_vnd": 300000, "stock_quantity": 5},
        {"product_id": "P002", "name": "Áo trắng", "brand": "Adidas", "category": "t_shirt", "color": "trắng", "description": "Áo thun có nhãn đỏ", "price_vnd": 500000, "stock_quantity": 2},
        {"product_id": "P003", "name": "Áo đen đỏ", "brand": "Nike", "category": "t_shirt", "color": "đen và đỏ rượu", "description": "Áo thun", "price_vnd": 700000, "stock_quantity": 3},
        {"product_id": "P004", "name": "Áo khoác xanh", "brand": "New Balance", "category": "jacket", "color": "xanh lá", "description": "Áo khoác", "price_vnd": 900000, "stock_quantity": 1},
    ]
    return CatalogSearch(SimpleNamespace(products=rows, fingerprint="test", summary=lambda p: dict(p)))


@pytest.mark.parametrize("text,expected", [
    ("không màu đỏ", ["P002", "P004"]),
    ("khong mau do va den", ["P002", "P004"]),
    ("không đỏ hoặc trắng", ["P004"]),
    ("không phải màu đỏ rượu", ["P001", "P002", "P004"]),
    ("except brand Nike", ["P002", "P004"]),
    ("ngoại trừ Nike và Adidas", ["P004"]),
    ("loại trừ thương hiệu New Balance", ["P001", "P002", "P003"]),
    ("trừ áo khoác", ["P001", "P002", "P003"]),
    ("without green", ["P001", "P002", "P003"]),
    ("not red or black; excluding Adidas", ["P004"]),
    ("không màu đỏ, không hãng Adidas", ["P004"]),
    ("không đỏ và không hãng Adidas", ["P004"]),
])
def test_exclusions_are_hard_metadata_constraints(catalog, text, expected):
    plan = catalog.exclusions.interpret(text)
    assert [p["product_id"] for p in catalog.products if plan.matches(p)] == expected
    assert plan.clauses
    result = catalog.browse(text, Filters(), "relevance", 0, 100)
    assert [p["product_id"] for p in result["products"]] == expected
    assert sum(f["count"] for f in result["facets"]["category"]) == len(expected)
    assert [p["product_id"] for p in catalog.suggestions(text, 10)] == expected


@pytest.mark.parametrize("text", ["không màu", "không hãng Unknown", "ngoại trừ Unknown", "không đỏ và Unknown", "không phải không đỏ", "not only red", "not Nike Air", "không đỏ và áo khoác", "not (red and black)"])
def test_ambiguous_explicit_scopes_do_not_silently_invert(catalog, text):
    with pytest.raises(AppError) as error:
        catalog.exclusions.interpret(text)
    assert (error.value.code, error.value.field) == ("EXCLUSION_QUERY_AMBIGUOUS", "text")
    disabled = catalog.exclusions.interpret(text, False)
    assert not disabled.clauses and disabled.lexical_text == text


@pytest.mark.parametrize("text", ["áo không tay", "áo không cổ", "túi không thấm nước", "không xác định", "Nike Air Max 270", "red shirt", "P001"])
def test_positive_or_ordinary_attributes_are_not_exclusions(catalog, text):
    plan = catalog.exclusions.interpret(text)
    assert not plan.clauses and plan.lexical_text == text


def test_original_unicode_spans_price_intersection_and_pagination(catalog):
    result = catalog.browse("ÁO; KHO\u0302NG MA\u0300U ĐO\u0309; dưới 600k", Filters(category="t_shirt"), "price_desc", 0, 1)
    assert result["total"] == 1 and result["products"][0]["product_id"] == "P002"
    assert result["exclusion_interpretation"]["clauses"] == [{"text": "KHÔNG MÀU ĐỎ", "field": "color", "value": "đỏ"}]
    assert result["price_interpretation"]["effective_filters"]["max_price"] == 599999
    assert result["query"]["filters"]["max_price"] is None
    assert catalog.browse("không đỏ", Filters(), "name", 10, 1)["products"] == []
    assert catalog.browse("không đỏ", Filters(color="đỏ"), "name", 0, 10, parse_exclusions=False)["total"] == 1


@pytest.mark.parametrize("filters,text,field", [(Filters(color="đen và đỏ rượu"), "không đỏ", "color"), (Filters(brand="Nike"), "trừ Nike", "brand"), (Filters(category="jacket"), "trừ áo khoác", "category")])
def test_manual_filters_conflict_explicitly(catalog, filters, text, field):
    with pytest.raises(AppError) as error:
        catalog.browse(text, filters, "relevance", 0, 10)
    assert (error.value.code, error.value.field) == ("EXCLUSION_FILTER_CONFLICT", f"filters.{field}")


@pytest.mark.parametrize("mode,strategy", [("text", "semantic"), ("text", "hybrid"), ("voice", "hybrid"), ("multimodal", "hybrid")])
def test_adversarial_high_scores_cannot_resurrect_excluded_products(catalog, tmp_path, mode, strategy):
    index = SimpleNamespace(available=True, fingerprint="a" * 64, product_vectors=np.tile(np.eye(1, 512, dtype=np.float32), (4, 1)),
                            retrieve=lambda _: [{"row": i, "product_id": p["product_id"], "score": .99 - .1 * i} for i, p in enumerate(catalog.products)])
    service = SearchService(catalog.repository, SimpleNamespace(available=True, model_fingerprint="b" * 64), index, tmp_path)
    text = "áo; không đỏ; dưới 600k"
    query = Query(mode, np.eye(1, 512)[0], None, None, SearchOptions(top_k=1, search_strategy=strategy), {"text": text})
    service.validate_request(query.options, mode, text)
    result = service.search(query)
    assert [r["product"]["product_id"] for r in result["results"]] == ["P002"]
    assert result["query"]["text"] == text
    assert result["meta"]["exclusion_interpretation"]["applied"]
    assert "do" not in catalog.prepare(result["meta"]["exclusion_interpretation"]["lexical_text"]).terms
    query.options.interpret_exclusions = False
    assert service.search(query)["results"][0]["product"]["product_id"] == "P001"


def test_limits_and_strict_http_optout(tmp_path, catalog):
    with pytest.raises(AppError):
        catalog.exclusions.interpret("a" * 501)
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "accounts.sqlite3"))) as api:
        for path in ("catalog", "suggestions"):
            assert api.get(f"/api/v1/{path}", params={"q": "khong mau", "interpret_exclusions": "false"}).status_code == 200
            assert api.get(f"/api/v1/{path}", params={"q": "khong mau"}).json()["error"]["code"] == "EXCLUSION_QUERY_AMBIGUOUS"
            assert api.get(f"/api/v1/{path}?interpret_exclusions=1").status_code == 422
            assert api.get(f"/api/v1/{path}?interpret_exclusions=false&interpret_exclusions=true").status_code == 422
        response = api.get("/api/v1/catalog", params={"q": "khong mau do", "color": "đỏ"})
        assert response.json()["error"]["code"] == "EXCLUSION_FILTER_CONFLICT"


def test_admin_metadata_case_english_colors_and_ambiguous_fields(catalog):
    rows = [dict(catalog.products[0], brand="Red", color="Red"), dict(catalog.products[1], brand="red", color="white")]
    interpretation = CatalogSearch(SimpleNamespace(products=rows, fingerprint="x", summary=lambda p: p)).exclusions
    with pytest.raises(AppError) as error:
        interpretation.interpret("not red")
    assert error.value.code == "EXCLUSION_QUERY_AMBIGUOUS"
    plan = interpretation.interpret("not color red")
    assert [p["product_id"] for p in rows if plan.matches(p)] == ["P002"]
    assert not any(interpretation.interpret("not brand red").matches(p) for p in rows)
