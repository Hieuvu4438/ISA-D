"""Prepare 30 deterministic demo orders; apply only against the expanded catalog.

The default writes an ignored runtime preview and never changes orders.json.
Existing O001–O003 and any already imported O004–O030 snapshots are preserved.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("processing", "shipped", "delivered", "cancelled")


def prepare_orders(products: list[dict], existing: list[dict]) -> list[dict]:
    """Keep historical snapshots, add only missing deterministic order IDs."""
    product_by_id = {product["product_id"]: product for product in products}
    if len(products) != 60 or len(product_by_id) != 60:
        raise ValueError("Import the 60-product catalog before preparing orders.")
    categories = Counter(product["category"] for product in products)
    if len(categories) != 12 or any(
        not 4 <= count <= 6 for count in categories.values()
    ):
        raise ValueError("Expected 12 fashion categories with 4–6 products each.")
    orders = {order["order_id"]: order for order in existing}
    if len(orders) != len(existing) or not {"O001", "O002", "O003"} <= orders.keys():
        raise ValueError("Existing orders must include unique O001, O002 and O003.")
    allowed_ids = {f"O{number:03d}" for number in range(1, 31)}
    if not orders.keys() <= allowed_ids:
        raise ValueError("Unexpected order IDs; refusing to replace unrelated orders.")
    sorted_products = sorted(products, key=lambda product: product["product_id"])
    cursor = 12
    for ordinal, number in enumerate(range(4, 31), start=1):
        order_id = f"O{number:03d}"
        item_count = 1 + (ordinal - 1) % 4
        items = []
        for item_index in range(item_count):
            product = sorted_products[(cursor + item_index) % len(sorted_products)]
            quantity = 1 + (ordinal + item_index) % 3
            price = product["price_vnd"]
            items.append(
                {
                    "product_id": product["product_id"],
                    "product_name": product["name"],
                    "quantity": quantity,
                    "unit_price_vnd": price,
                    "line_total_vnd": quantity * price,
                }
            )
        cursor += item_count
        when = datetime(2026, 9, 15, 7, 30, tzinfo=timezone.utc) + timedelta(
            days=(ordinal - 1) % 22
        )
        generated = {
            "order_id": order_id,
            "customer_id": "C002" if ordinal % 5 == 0 else "C001",
            "date": when.isoformat().replace("+00:00", "Z"),
            "status": STATUSES[(ordinal - 1) % len(STATUSES)],
            "items": items,
            "total_vnd": sum(item["line_total_vnd"] for item in items),
        }
        # Historical names/prices remain snapshots on a second run.
        if order_id not in orders:
            orders[order_id] = generated
    result = [orders[key] for key in sorted(orders)]
    validate_orders(result, product_by_id)
    return result


def validate_orders(orders: list[dict], products: dict[str, dict]) -> None:
    if len(orders) != 30 or Counter(order["customer_id"] for order in orders) != {
        "C001": 24,
        "C002": 6,
    }:
        raise ValueError(
            "The demo must contain 30 orders: 24 scoped to C001 and 6 to C002."
        )
    for order in orders:
        if set(order) != {
            "order_id",
            "customer_id",
            "date",
            "status",
            "items",
            "total_vnd",
        }:
            raise ValueError(f"Unexpected order fields: {order['order_id']}")
        when = datetime.fromisoformat(order["date"].replace("Z", "+00:00"))
        if (
            when.utcoffset() != timedelta(0)
            or order["status"] not in STATUSES
            or not 1 <= len(order["items"]) <= 4
        ):
            raise ValueError(f"Invalid order metadata: {order['order_id']}")
        for item in order["items"]:
            if set(item) != {
                "product_id",
                "product_name",
                "quantity",
                "unit_price_vnd",
                "line_total_vnd",
            }:
                raise ValueError("Unexpected item fields")
            if (
                item["product_id"] not in products
                or not isinstance(item["product_name"], str)
                or not item["product_name"]
            ):
                raise ValueError("Unknown product or empty snapshot name")
            if type(item["quantity"]) is not int or not 1 <= item["quantity"] <= 3:
                raise ValueError("Invalid demo item quantity")
            if type(item["unit_price_vnd"]) is not int or item["unit_price_vnd"] < 0:
                raise ValueError("Invalid snapshot price")
            if (
                type(item["line_total_vnd"]) is not int
                or item["line_total_vnd"] != item["quantity"] * item["unit_price_vnd"]
            ):
                raise ValueError("Incorrect item total")
        if type(order["total_vnd"]) is not int or order["total_vnd"] != sum(
            item["line_total_vnd"] for item in order["items"]
        ):
            raise ValueError("Incorrect order total")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Atomically replace orders.json with the validated seed",
    )
    args = parser.parse_args()
    products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
    destination = ROOT / "data/orders.json"
    existing = json.loads(destination.read_text(encoding="utf-8"))
    prepared = prepare_orders(products, existing)
    content = json.dumps(prepared, ensure_ascii=False, indent=2) + "\n"
    if args.apply:
        if prepared != existing:
            temporary = destination.with_suffix(".json.tmp")
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(destination)
    else:
        preview = ROOT / "runtime/order-seed-preview.json"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_text(content, encoding="utf-8")
    summary = {
        "applied": args.apply,
        "changed": prepared != existing,
        "order_count": len(prepared),
        "customers": dict(Counter(order["customer_id"] for order in prepared)),
        "statuses": dict(Counter(order["status"] for order in prepared)),
        "distinct_products_ordered": len(
            {item["product_id"] for order in prepared for item in order["items"]}
        ),
        "original_orders_preserved": all(
            next(order for order in prepared if order["order_id"] == key)
            == next(order for order in existing if order["order_id"] == key)
            for key in ("O001", "O002", "O003")
        ),
        "destination": "data/orders.json"
        if args.apply
        else "runtime/order-seed-preview.json",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
