from pathlib import Path
import json
import shutil
import pytest

from app.data.product_repository import ProductRepository
from app.data.order_repository import OrderRepository
from app.domain import AppError

ROOT = Path(__file__).resolve().parents[2]


def test_catalog_real_images_credits_and_immutable_snapshot():
    repo = ProductRepository(ROOT)
    expected_ids = {p["product_id"] for p in json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))}
    assert {p["product_id"] for p in repo.products} == expected_ids
    assert {credit["product_id"] for credit in repo.credits()} == expected_ids
    for product in repo.products:
        path, mime, checksum = repo.image_file(product["product_id"])
        assert path.is_file() and mime == "image/jpeg" and len(checksum) == 64
        assert "image_path" not in repo.detail(product)
        assert repo.detail(product)["image_credit"]["source_page"].startswith("https://")
    products = repo.all_products()
    products[0]["name"] = "mutated"
    assert repo.get_by_id("P001")["name"] != "mutated"


def test_orders_customer_scope_and_snapshot_totals():
    repo = OrderRepository(ROOT)
    assert repo.find_order("C001", "O001")["total_vnd"] > 0
    assert repo.find_order("C001", "O002") is None
    assert repo.find_order("C001", "O999") is None
    for order in repo.orders:
        assert order["total_vnd"] == sum(item["line_total_vnd"] for item in order["items"])


@pytest.mark.parametrize(
    "field,value",
    [("price_vnd", True), ("stock_quantity", -1), ("image_path", "../outside.jpg"), ("product_id", "bad")],
)
def test_invalid_catalog_rejected_before_serving(tmp_path, field, value):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    path = tmp_path / "data/products.json"
    products = json.loads(path.read_text(encoding="utf-8"))
    products[0][field] = value
    path.write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AppError) as error:
        ProductRepository(tmp_path)
    assert error.value.code == "CATALOG_UNAVAILABLE"


def test_modified_real_image_checksum_rejected(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    path = tmp_path / "data/images/P001.jpg"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(AppError):
        ProductRepository(tmp_path)


def test_invalid_order_money_rejected(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    path = tmp_path / "data/orders.json"
    orders = json.loads(path.read_text(encoding="utf-8"))
    orders[0]["total_vnd"] += 1
    path.write_text(json.dumps(orders, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AppError) as error:
        OrderRepository(tmp_path)
    assert error.value.code == "ORDERS_UNAVAILABLE"
