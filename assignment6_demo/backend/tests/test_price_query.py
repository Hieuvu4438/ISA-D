from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.application.catalog_search import CatalogSearch
from app.application.price_query import interpret_price
from app.application.search_service import SearchService
from app.data.product_repository import ProductRepository
from app.domain import AppError, Filters, SearchOptions
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("text,lower,upper", [
    ("áo thun dưới 1 triệu", None, 999999), ("ao thun duoi 1tr", None, 999999),
    ("giày không quá 1,5 triệu", None, 1500000), ("giay toi da 1.5tr", None, 1500000),
    ("áo ít nhất 500 nghìn", 500000, None), ("túi trên 500k", 500001, None),
    ("đồng hồ không dưới 500 ngàn", 500000, None), ("áo không hơn 1 triệu", None, 1000000),
    ("áo từ 500 nghìn đến 1,5 triệu", 500000, 1500000),
    ("shoes between 500k and 1 million", 500000, 1000000),
    ("áo từ 500 đến 1500k", 500000, 1500000), ("áo từ 500k đến 1500", 500000, 1500000),
    ("áo giá dưới 1.500.000 VND", None, 1499999), ("áo dưới 1,500,000 đ", None, 1499999),
    ("túi dưới 1 500 000 đồng", None, 1499999), ("túi dưới 1500000", None, 1499999),
    ("áo dưới 1 triệu rưỡi", None, 1499999), ("áo dưới 1 triệu 500 nghìn", None, 1499999),
    ("áo dưới 1tr500k", None, 1499999), ("under 1.25 million", None, 1249999),
    ("shoes at most 500 thousand", None, 500000), ("bag no more than 500k", None, 500000),
    ("áo dưới 0,5 đ", None, 0), ("áo trên 0,5 đ", 1, None),
    ("áo không quá 0 đ", None, 0), ("áo từ 0 đ đến 1000000000 VND", 0, 1000000000),
    ("áo trên 500k dưới 1 triệu", 500001, 999999), ("áo không rẻ hơn 1 triệu", 1000000, None),
    ("áo không đắt hơn 1 triệu", None, 1000000), ("áo dưới +1 triệu", None, 999999),
    ("áo <1tr", None, 999999), ("áo <= 1tr", None, 1000000),
    ("áo ≥500k", 500000, None), ("áo >500k", 500001, None),
    ("áo dưới một triệu", None, 999999), ("áo dưới một triệu rưỡi", None, 1499999),
    ("áo từ năm trăm nghìn đến một triệu", 500000, 1000000),
    ("áo không quá một triệu hai trăm nghìn", None, 1200000),
    ("áo trên chín trăm chín mươi chín nghìn", 999001, None),
    ("áo dưới một trăm lẻ năm nghìn", None, 104999),
    ("áo dưới hai mươi mốt nghìn", None, 20999), ("áo dưới mười lăm nghìn", None, 14999),
])
def test_explicit_price_grammar_integer_boundaries(text, lower, upper):
    plan = interpret_price(text)
    assert (plan.min_price, plan.max_price) == (lower, upper)
    assert plan.clauses
    assert plan.public(plan.merge(Filters()))["applied"] is True


@pytest.mark.parametrize("text,code", [
    ("áo dưới 0đ", "PRICE_QUERY_CONFLICT"), ("áo trên 1000000000 VND", "PRICE_QUERY_CONFLICT"),
    ("áo từ 2tr đến 1tr", "PRICE_QUERY_CONFLICT"), ("áo trên 2tr dưới 1tr", "PRICE_QUERY_CONFLICT"),
    ("áo dưới -1 triệu", "PRICE_VALUE_UNSUPPORTED"), ("áo dưới 2000 triệu", "PRICE_VALUE_UNSUPPORTED"),
    ("áo dưới 1.500 triệu", "PRICE_QUERY_AMBIGUOUS"), ("áo dưới 1,500 triệu", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới 1.000,50 VND", "PRICE_QUERY_AMBIGUOUS"), ("áo dưới 1.2.3tr", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới 500", "PRICE_QUERY_AMBIGUOUS"), ("áo 500k", "PRICE_QUERY_AMBIGUOUS"),
    ("áo khoảng dưới 1tr", "PRICE_QUERY_AMBIGUOUS"), ("áo khoảng 1tr", "PRICE_QUERY_AMBIGUOUS"),
    ("áo không muốn dưới 1tr", "PRICE_QUERY_AMBIGUOUS"), ("áo not under 1 million", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới 1tr hoặc trên 2tr", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới 1tr hay trên 2tr", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới 1,2 triệu rưỡi", "PRICE_QUERY_AMBIGUOUS"), ("áo dưới 1 triệu 1500k", "PRICE_QUERY_AMBIGUOUS"),
    ("áo under $50", "PRICE_CURRENCY_UNSUPPORTED"), ("áo dưới 100USD", "PRICE_CURRENCY_UNSUPPORTED"),
    ("áo giá dưới 1m", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới một hai triệu", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới một trăm lẻ triệu", "PRICE_QUERY_AMBIGUOUS"),
])
def test_ambiguous_conflicting_and_out_of_range_fail_explicitly(text, code):
    with pytest.raises(AppError) as error:
        interpret_price(text)
    assert error.value.status == 422 and error.value.code == code


def test_unicode_source_spans_literal_queries_and_optout():
    text = "ÁO GIA\u0301 DU\u031bO\u031b\u0301I 1 TRIỆU"
    plan = interpret_price(text)
    assert plan.lexical_text == "ÁO" and plan.max_price == 999999
    assert plan.clauses[0]["text"] == "GIÁ DƯỚI 1 TRIỆU"
    for text in ["Nike Air Max 270", "áo thun size 40", "đồng hồ 100m", "P001", "shirt!!!", "áo không tay"]:
        plan = interpret_price(text)
        assert plan.clauses == [] and plan.lexical_text == text
    disabled = interpret_price("áo khoảng 1tr", False)
    assert disabled.clauses == [] and disabled.lexical_text == "áo khoảng 1tr"


def test_intersection_with_manual_filters_never_broadens_or_mutates():
    filters = Filters(min_price=700000, max_price=2000000, category="t_shirt", in_stock=True)
    effective = interpret_price("áo trên 500k dưới 1tr").merge(filters)
    assert effective.min_price == 700000 and effective.max_price == 999999
    assert filters.max_price == 2000000 and effective.category == "t_shirt" and effective.in_stock
    with pytest.raises(AppError) as error:
        interpret_price("áo dưới 1tr").merge(Filters(min_price=2000000))
    assert error.value.code == "PRICE_FILTER_CONFLICT"


def test_catalog_hard_price_filter_before_pagination_facets_and_suggestions():
    catalog = CatalogSearch(ProductRepository(ROOT))
    page = catalog.browse("áo thun dưới 1 triệu", Filters(), "price_desc", 0, 3)
    expected = catalog.browse("áo thun", Filters(max_price=999999), "price_desc", 0, 3)
    assert page["products"] == expected["products"] and page["total"] == expected["total"] > 0
    assert page["facets"] == expected["facets"]
    assert page["query"]["filters"]["max_price"] is None
    assert page["price_interpretation"]["effective_filters"]["max_price"] == 999999
    assert all(p["price_vnd"] < 1000000 for p in catalog.suggestions("áo thun dưới 1 triệu", 10))
    assert catalog.browse("P001 dưới 1 triệu", Filters(), "relevance", 0, 20)["total"] == 0
    assert catalog.browse("tôi cần giá dưới 1 triệu", Filters(), "relevance", 0, 20)["total"] > 0


def test_search_validates_price_conflict_before_encoder_and_keeps_optout(tmp_path):
    products = ProductRepository(ROOT)
    service = SearchService(products, SimpleNamespace(available=True), SimpleNamespace(available=False), tmp_path)
    with pytest.raises(AppError) as error:
        service.validate_request(SearchOptions(filters=Filters(min_price=2000000)), "text", "áo dưới 1tr")
    assert error.value.code == "PRICE_FILTER_CONFLICT"
    service.validate_request(SearchOptions(interpret_price=False), "text", "áo khoảng 1tr")


def test_public_catalog_contract_and_strict_optout(tmp_path):
    with TestClient(create_app(Settings(root=ROOT, load_models=False, account_db_path=tmp_path / "db.sqlite3"))) as client:
        result = client.get("/api/v1/catalog", params={"q": "áo thun dưới 1 triệu", "limit": 2})
        assert result.status_code == 200
        assert all(p["price_vnd"] < 1000000 for p in result.json()["products"])
        assert result.json()["price_interpretation"]["applied"] is True
        assert client.get("/api/v1/catalog", params={"q": "áo thun dưới 1 triệu", "min_price": 2000000}).json()["error"]["code"] == "PRICE_FILTER_CONFLICT"
        assert client.get("/api/v1/catalog", params={"q": "áo khoảng 1tr"}).status_code == 422
        assert client.get("/api/v1/catalog", params={"q": "áo khoảng 1tr", "interpret_price": "false"}).status_code == 200
        for endpoint in ("catalog", "suggestions"):
            assert client.get(f"/api/v1/{endpoint}?interpret_price=1").status_code == 422
            assert client.get(f"/api/v1/{endpoint}?interpret_price=true&interpret_price=false").status_code == 422
