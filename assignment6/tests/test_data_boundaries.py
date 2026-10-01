"""Invalid local data must fail at boundaries, not inside retrieval."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from application.order_service import OrderService
from application.query_service import QueryService
from application.ranking_service import RankingService
from data.order_repository import OrderRepository
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex, cosine_similarity
from main import build_services
from scripts.prepare_dataset import prepare

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "missing",
        "duplicate",
        "price_nan",
        "price_negative",
        "stock_bool",
        "name_empty",
        "category_wrong",
        "image_missing",
        "id_bool",
    ],
)
def test_product_schema_rejects_invalid_data(tmp_path, mutation):
    products = json.loads((ROOT / "data/products.json").read_text())
    if mutation == "empty":
        products = []
    elif mutation == "missing":
        del products[0]["name"]
    elif mutation == "duplicate":
        products[1]["product_id"] = products[0]["product_id"]
    else:
        key, value = {
            "price_nan": ("price", float("nan")),
            "price_negative": ("price", -1),
            "stock_bool": ("stock", True),
            "name_empty": ("name", ""),
            "category_wrong": ("category", "food"),
            "image_missing": ("image", "data/images/missing.png"),
            "id_bool": ("product_id", True),
        }[mutation]
        products[0][key] = value
    with pytest.raises(ValueError):
        ProductRepository(write(tmp_path / "products.json", products), ROOT)


def test_product_load_error(tmp_path):
    with pytest.raises(ValueError):
        ProductRepository(tmp_path / "missing.json")


@pytest.mark.parametrize("mutation", ["not_list", "missing", "duplicate", "blank", "negative"])
def test_order_schema_rejects_invalid_data(tmp_path, mutation):
    orders = json.loads((ROOT / "data/orders.json").read_text())
    if mutation == "not_list":
        orders = {}
    elif mutation == "missing":
        del orders[0]["status"]
    elif mutation == "duplicate":
        orders[1]["order_id"] = orders[0]["order_id"]
    elif mutation == "blank":
        orders[0]["customer_id"] = ""
    else:
        orders[0]["total"] = -1
    with pytest.raises(ValueError):
        OrderRepository(write(tmp_path / "orders.json", orders))


def test_order_bad_id_and_load_errors(tmp_path):
    with pytest.raises(ValueError):
        OrderRepository(tmp_path / "missing.json")
    with pytest.raises(ValueError):
        OrderService(OrderRepository()).find_order("invalid", "C001")


@pytest.mark.parametrize("mutation", ["encoder", "dimension", "ids", "fingerprint", "missing"])
def test_index_consistency_and_stale_detection(tmp_path, mutation):
    payload = json.loads((ROOT / "data/embeddings.json").read_text())
    if mutation == "encoder":
        payload["encoder"]["version"] = "unknown"
    elif mutation == "dimension":
        payload["vectors"]["1"] = [1, 2]
    elif mutation == "ids":
        del payload["vectors"]["1"]
    elif mutation == "fingerprint":
        payload["source_sha256"] = "stale"
    else:
        del payload["encoder"]
    with pytest.raises(ValueError):
        VectorIndex(write(tmp_path / "index.json", payload), ProductRepository().all_products(), ROOT)


def test_invalid_cosine_and_index_query():
    with pytest.raises(ValueError):
        cosine_similarity(["nonnumeric"], [1])
    with pytest.raises(ValueError):
        VectorIndex().score([1])


@pytest.mark.parametrize(
    "options",
    [{"category": "food"}, {"max_price": -1}, {"max_price": float("inf")}, {"max_price": True}, {"category": "bag"}],
)
def test_query_filter_boundary(options):
    with pytest.raises(ValueError):
        QueryService().text_query("shoes", **options)


def test_query_price_minimum_and_stopword_only():
    assert QueryService().text_query("shoes under 100 below 80")["filters"]["max_price_exclusive"] == 80
    assert QueryService().text_query("shoes", max_price=60)["filters"]["max_price_exclusive"] == 60
    with pytest.raises(ValueError):
        QueryService().text_query("find me please")
    with pytest.raises(ValueError):
        QueryService().image_query(["nonnumeric"] * 88)


def test_extracted_price_overflow_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        QueryService().text_query("shoes under " + "9" * 400)


def test_dataset_generator_rejects_paths_outside_root(tmp_path):
    products = json.loads((ROOT / "data/products.json").read_text())
    products[0]["image"] = "../escaped.png"
    catalogue = tmp_path / "data/products.json"
    catalogue.parent.mkdir()
    write(catalogue, products)
    with pytest.raises(ValueError, match="inside"):
        prepare(tmp_path)
    assert not (tmp_path.parent / "escaped.png").exists()


def test_ranking_boundary_and_no_hidden_stock_signal():
    ranker = RankingService()
    q = QueryService().text_query("backpack")
    candidates = [
        dict(product_id=12, stock=0, text_score=1, image_score=0),
        dict(product_id=9, stock=10, text_score=0.5, image_score=0),
    ]
    assert ranker.rank(candidates, q)[0]["product_id"] == 12
    original = deepcopy(candidates)
    q["weights"] = {"text": 0.5, "image": 0.6}
    with pytest.raises(ValueError):
        ranker.rank(candidates, q)
    assert candidates == original


def test_search_rejects_unsupported_contract():
    ui = build_services()
    with pytest.raises(ValueError):
        ui.search_service.search({"type": "unknown"})
    with pytest.raises(ValueError):
        ui.view_product(-1)


def test_dataset_regeneration_preserves_customized_files(tmp_path):
    prepare(tmp_path)
    catalogue = tmp_path / "data/products.json"
    products = json.loads(catalogue.read_text())
    products[0]["price"] = 123
    write(catalogue, products)
    image = tmp_path / "data/images/p001.png"
    before = image.read_bytes()
    prepare(tmp_path)
    assert json.loads(catalogue.read_text())[0]["price"] == 123
    assert image.read_bytes() == before
