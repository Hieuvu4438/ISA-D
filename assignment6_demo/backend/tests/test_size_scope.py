"""Variant-backed size intent, with intentionally stale seed stock and wrong AI ranks."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.application.catalog_search import CatalogSearch
from app.application.query_service import Query
from app.application.search_service import SearchService
from app.domain import SUPPORTED_SIZES, AppError, Filters, SearchOptions
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def catalog():
    rows = [dict(product_id=pid, name=name, brand="Nike", category=category, color="trắng", description=name,
                 price_vnd=price, stock_quantity=999) for pid, name, category, price in [
        ("P001", "Áo thun trắng", "t_shirt", 300000), ("P002", "Áo thun trắng", "t_shirt", 500000),
        ("P003", "Giày chạy bộ", "running_shoes", 800000), ("P004", "Balo trắng", "backpack", 900000),
        ("P005", "Áo thun chưa phân cỡ", "t_shirt", 400000), ("P006", "Áo thun hết hàng", "t_shirt", 200000),
    ]]
    service = CatalogSearch(SimpleNamespace(products=rows, fingerprint="size-fixture", summary=lambda p: dict(p)))
    service.stock = {"P001": 5, "P002": 3, "P003": 2, "P004": 1, "P005": 10, "P006": 0}
    service.sizes = {pid: [{"size": size, "stock_quantity": qty} for size, qty in variants] for pid, variants in {
        "P001": [("M", 0), ("L", 5)], "P002": [("M", 3), ("L", 0)], "P003": [("40", 2), ("42", 0)],
        "P004": [("ONE", 1)], "P006": [("M", 0)],
    }.items()}
    service.archived = set()
    service.inventory = SimpleNamespace(snapshot_catalog=lambda: (service.stock, 7, service.sizes, service.archived))
    return service


@pytest.mark.parametrize("text,ids", [
    ("áo thun size M", ["P001", "P002", "P006"]),
    ("AO THUN SIZE m", ["P001", "P002", "P006"]),
    ("a\u0301o thun cơ\u0303 M", ["P001", "P002", "P006"]),
    ("áo thun co M", ["P001", "P002", "P006"]),
    ("áo thun kích cỡ M", ["P001", "P002", "P006"]),
    ("áo thun sizeM", ["P001", "P002", "P006"]),
    ("áo thun size M hoặc L", ["P001", "P002", "P006"]),
    ("áo thun size M hoặc size L", ["P001", "P002", "P006"]),
    ("áo thun cỡ M hoặc kích cỡ L", ["P001", "P002", "P006"]),
    ("áo thun size XL", []),
    ("giày chạy bộ size40", ["P003"]),
    ("giày chạy bộ cỡ 42", ["P003"]),
    ("giày chạy bộ cỡ 40 hoặc 42", ["P003"]),
    ("áo thun size3XL", []),
    ("balo size ONE", ["P004"]),
    ("áo thun màu trắng hãng Nike size M; dưới 400k", ["P001", "P006"]),
    ("áo thun size M P001", ["P001"]),
    ("áo thun size M P999", []),
])
def test_known_size_scope_and_suggestions_use_live_variant_definitions(catalog, text, ids):
    result = catalog.browse(text, Filters(), "relevance", 0, 20)
    assert [p["product_id"] for p in result["products"]] == ids
    assert any(c["field"] == "size" for c in result["scope_interpretation"]["clauses"])
    assert [p["product_id"] for p in catalog.suggestions(text, 10)] == ids
    assert all("_variants" not in p and p["stock_quantity"] == 999 for p in catalog.products)


@pytest.mark.parametrize("text", [
    "áo size M và L", "áo size M,L", "áo size M/L", "áo size M-L", "giày size 40.5", "giày size 40,5",
    "giày size >=40", "giày size 40-42", "áo size 9XL", "áo size potato", "áo size", "áo cỡ",
    "áo kích cỡ", "áo size M hoặc", "áo cỡ M hoặc", "size M hoặc Nike", "Nike hoặc size M",
    "áo không size M", "áo size M giống L",
])
def test_unknown_incomplete_comparison_and_unsupported_size_syntax_preserve_query(catalog, text):
    plan = catalog.scopes.interpret(text)
    assert plan.warnings
    assert not plan.clauses
    assert plan.lexical_text == text
    assert not catalog.scopes.interpret(text, False).warnings


def test_numbers_and_vietnamese_have_are_not_size_markers(catalog):
    for text in ["áo có màu trắng", "tôi có áo thun", "toi co ao thun", "42", "mẫu 42 mới", "mẫu sizeguide"]:
        assert not [c for c in catalog.scopes.interpret(text).clauses if c["field"] == "size"]
    assert catalog.scopes.interpret("áo có màu trắng").warnings == []
    for size in SUPPORTED_SIZES:
        assert Filters(size=size).size == size


def test_stock_filter_checks_requested_size_not_other_size_or_seed_stock(catalog):
    result = catalog.browse("áo thun size M", Filters(in_stock=True), "relevance", 0, 10)
    assert [p["product_id"] for p in result["products"]] == ["P002"]
    assert {c["value"]: c["count"] for c in result["facets"]["size"]} == {"40": 0, "42": 0, "L": 0, "M": 1, "ONE": 0}
    catalog.stock["P001"] = 7
    catalog.sizes["P001"][0]["stock_quantity"] = 2
    result = catalog.browse("áo thun size M", Filters(in_stock=True), "relevance", 0, 10)
    assert [p["product_id"] for p in result["products"]] == ["P001", "P002"]
    catalog.archived.add("P002")
    assert [p["product_id"] for p in catalog.suggestions("áo thun size M", 10)] == ["P001", "P006"]


def test_manual_size_conflict_union_and_opt_out(catalog):
    with pytest.raises(AppError) as error:
        catalog.browse("áo thun size M", Filters(size="L"), "relevance", 0, 10)
    assert error.value.code == "SCOPE_FILTER_CONFLICT" and error.value.field == "filters.size"
    result = catalog.browse("áo thun size M hoặc L", Filters(size="L", in_stock=True), "relevance", 0, 10)
    assert [p["product_id"] for p in result["products"]] == ["P001"]
    assert not catalog.scopes.interpret("size M", False).clauses


@pytest.mark.parametrize("mode,strategy", [("text", "semantic"), ("text", "hybrid"), ("voice", "hybrid"), ("multimodal", "hybrid")])
def test_size_and_stock_hard_filter_before_wrong_model_ranking(catalog, tmp_path, mode, strategy):
    index = SimpleNamespace(available=True, fingerprint="a" * 64,
                            product_vectors=np.tile(np.eye(1, 512, dtype=np.float32), (len(catalog.products), 1)),
                            retrieve=lambda _: [{"row": i, "product_id": p["product_id"], "score": .1 if p["product_id"] == "P002" else .99} for i, p in enumerate(catalog.products)])
    service = SearchService(catalog.repository, SimpleNamespace(available=True, model_fingerprint="b" * 64), index, tmp_path)
    service.inventory = catalog.inventory
    text = "áo thun size M"
    options = SearchOptions(top_k=1, search_strategy=strategy, filters=Filters(in_stock=True))
    query = Query(mode, np.eye(1, 512)[0], None, None, options, {"text": text})
    service.validate_request(options, mode, text)
    result = service.search(query)
    assert [r["product"]["product_id"] for r in result["results"]] == ["P002"]
    assert result["query"]["text"] == text
    assert all("_variants" not in p and p["stock_quantity"] == 999 for p in catalog.products)
    with pytest.raises(AppError) as error:
        service.validate_request(SearchOptions(filters=Filters(size="L")), mode, text)
    assert error.value.field == "options.filters.size"


def test_http_variant_allocation_stock_change_and_restart(tmp_path):
    db = tmp_path / "size-scope.sqlite3"
    settings = Settings(root=ROOT, load_models=False, account_db_path=db)
    with TestClient(create_app(settings)) as api:
        user = api.post('/api/v1/auth/register', headers={"X-Cortis-Intent": "account"}, json={
            "email": "size-query@example.test", "password": "size query test passphrase 2026", "display_name": "Size query admin"}).json()["user"]
        with api.app.state.accounts.repository.connection() as connection:
            connection.execute("UPDATE accounts SET role='admin' WHERE user_id=?", (user["user_id"],))
        revision = api.get('/api/v1/admin/inventory').json()["revision"]
        for size, qty in [("M", 0), ("L", 2)]:
            r = api.post('/api/v1/admin/products/P041/variants', headers={"X-Cortis-Intent": "admin"}, json={"size": size, "quantity": qty, "revision": revision, "reason": "Size query lifecycle test"})
            assert r.status_code == 201, r.text
            revision = r.json()["variant"]["revision"]
        query = "áo thun size M P041"
        assert api.get('/api/v1/catalog', params={"q": query}).json()["total"] == 1
        assert api.get('/api/v1/catalog', params={"q": query, "in_stock": "true"}).json()["products"] == []
        suggestions = api.get('/api/v1/suggestions', params={"q": query}).json()["products"]
        assert [p["product_id"] for p in suggestions] == ["P041"]
        assert suggestions[0]["available_sizes"] == ["L"]
        r = api.post('/api/v1/admin/inventory/P041-M', headers={"X-Cortis-Intent": "admin"}, json={"quantity": 1, "revision": revision, "reason": "Restore requested size"})
        assert r.status_code == 200, r.text
        assert api.get('/api/v1/catalog', params={"q": query, "in_stock": "true"}).json()["total"] == 1
        assert api.get('/api/v1/catalog', params={"q": query, "size": "L"}).status_code == 422
    with TestClient(create_app(settings)) as api:
        result = api.get('/api/v1/catalog', params={"q": query, "in_stock": "true"}).json()
        assert result["total"] == 1
        assert "M" in result["products"][0]["available_sizes"]
