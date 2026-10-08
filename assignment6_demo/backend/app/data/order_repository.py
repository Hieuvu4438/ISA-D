import copy
import json
import re
from datetime import datetime
from pathlib import Path

from app.domain import AppError


class OrderRepository:
    def __init__(self, root: Path):
        try:
            self._orders = json.loads((Path(root) / "data/orders.json").read_text(encoding="utf-8"))
            ids = set()
            product_ids = {
                p["product_id"] for p in json.loads((Path(root) / "data/products.json").read_text(encoding="utf-8"))
            }
            for order in self._orders:
                if (
                    set(order) != {"order_id", "customer_id", "date", "status", "items", "total_vnd"}
                    or not re.fullmatch(r"O[0-9]{3}", order["order_id"])
                    or order["order_id"] in ids
                    or not re.fullmatch(r"C[0-9]{3}", order["customer_id"])
                ):
                    raise ValueError("order schema")
                ids.add(order["order_id"])
                date = datetime.fromisoformat(order["date"].replace("Z", "+00:00"))
                if (
                    date.utcoffset() is None
                    or date.utcoffset().total_seconds() != 0
                    or order["status"] not in ("processing", "shipped", "delivered", "cancelled")
                    or not order["items"]
                ):
                    raise ValueError("order metadata")
                for item in order["items"]:
                    if (
                        set(item) != {"product_id", "product_name", "quantity", "unit_price_vnd", "line_total_vnd"}
                        or item["product_id"] not in product_ids
                        or not item["product_name"]
                    ):
                        raise ValueError("item schema")
                    if (
                        type(item["quantity"]) is not int
                        or not 1 <= item["quantity"] <= 100
                        or any(type(item[f]) is not int or item[f] < 0 for f in ("unit_price_vnd", "line_total_vnd"))
                    ):
                        raise ValueError("item numeric")
                    if item["line_total_vnd"] != item["quantity"] * item["unit_price_vnd"]:
                        raise ValueError("line total")
                if type(order["total_vnd"]) is not int or order["total_vnd"] != sum(
                    i["line_total_vnd"] for i in order["items"]
                ):
                    raise ValueError("total")
        except Exception as exc:
            raise AppError(503, "ORDERS_UNAVAILABLE", "Dữ liệu đơn hàng chưa sẵn sàng.") from exc

    @property
    def orders(self):
        return copy.deepcopy(self._orders)

    def find_order(self, customer_id, order_id):
        return copy.deepcopy(
            next((o for o in self._orders if o["customer_id"] == customer_id and o["order_id"] == order_id), None)
        )
