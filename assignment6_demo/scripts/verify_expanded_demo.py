"""Verify the running 60-product, 12-category, 30-order demo without Azure calls.

Run after rebuilding the index, calibrating policies and restarting the backend.
Semantic category probes are measured separately from API correctness gates.
Catalog-photo reuse is an alignment smoke, never a held-out quality evaluation.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[1]
CATEGORY_QUERIES = {
    "running_shoes": "giày chạy bộ thể thao",
    "trail_shoes": "giày chạy địa hình",
    "casual_shoes": "giày sneaker thường ngày",
    "boots": "giày boots cổ cao",
    "sandals": "dép sandal mùa hè",
    "bag": "túi xách thời trang",
    "backpack": "balo đeo lưng",
    "tote_bag": "túi tote vải có quai xách",
    "t_shirt": "áo thun ngắn tay",
    "jacket": "áo khoác",
    "watch": "đồng hồ đeo tay",
    "sunglasses": "kính râm thời trang",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    return value if re.fullmatch(r"[a-f0-9]{40}", value) else None


def public_summary(product: dict) -> dict:
    return {
        **{
            key: product[key]
            for key in ("product_id", "name", "category", "brand", "color", "price_vnd")
        },
        "in_stock": product["stock_quantity"] > 0,
        "image_url": f"/api/v1/media/products/{product['product_id']}",
    }


def private_keys_absent(value) -> bool:
    # A validation field may legitimately *name* a rejected customer_id input.
    # The prohibition concerns server/private properties, not that field label.
    if isinstance(value, dict):
        return not ({"customer_id", "local_path", "image_path"} & value.keys()) and all(
            private_keys_absent(child) for child in value.values()
        )
    if isinstance(value, list):
        return all(private_keys_absent(child) for child in value)
    return True


def expected_ids(products: list[dict], filters: dict) -> set[str]:
    return {
        product["product_id"]
        for product in products
        if (
            filters.get("category") is None
            or product["category"] == filters["category"]
        )
        and (filters.get("brand") is None or product["brand"] == filters["brand"])
        and (
            filters.get("min_price") is None
            or product["price_vnd"] >= filters["min_price"]
        )
        and (
            filters.get("max_price") is None
            or product["price_vnd"] <= filters["max_price"]
        )
        and (not filters.get("in_stock") or product["stock_quantity"] > 0)
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    location = urlsplit(args.base_url)
    if (
        location.scheme not in ("http", "https")
        or location.hostname not in ("127.0.0.1", "localhost", "::1")
        or location.username
        or location.password
        or location.query
        or location.fragment
        or location.path not in ("", "/")
    ):
        parser.error("Use a local backend origin without credentials, query or path.")
    started = time.perf_counter()
    products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
    orders = json.loads((ROOT / "data/orders.json").read_text(encoding="utf-8"))
    assets = json.loads((ROOT / "data/image_sources.json").read_text(encoding="utf-8"))[
        "assets"
    ]
    by_id = {product["product_id"]: product for product in products}
    assets_by_id = {asset["asset_id"]: asset for asset in assets}
    checks: list[dict] = []
    semantic: list[dict] = []
    alignment: list[dict] = []
    ood: list[dict] = []
    meta: dict = {}

    def run(name, action):
        before = time.perf_counter()
        try:
            evidence = action() or {}
            checks.append(
                {
                    "name": name,
                    "passed": True,
                    "duration_ms": round((time.perf_counter() - before) * 1000, 3),
                    **evidence,
                }
            )
        except (
            AssertionError,
            KeyError,
            ValueError,
            TypeError,
            OSError,
            httpx.HTTPError,
        ) as exc:
            # Do not persist raw HTTP bodies, local paths or exception messages.
            checks.append(
                {
                    "name": name,
                    "passed": False,
                    "failure_type": type(exc).__name__,
                    "duration_ms": round((time.perf_counter() - before) * 1000, 3),
                }
            )

    def local_shape():
        categories = Counter(product["category"] for product in products)
        assert len(products) == len(by_id) == 60
        assert set(categories) == set(CATEGORY_QUERIES)
        assert all(4 <= count <= 6 for count in categories.values())
        assert len(orders) == 30 and len({order["order_id"] for order in orders}) == 30
        assert Counter(order["customer_id"] for order in orders) == {
            "C001": 24,
            "C002": 6,
        }
        assert {order["status"] for order in orders} == {
            "processing",
            "shipped",
            "delivered",
            "cancelled",
        }
        return {
            "product_count": len(products),
            "category_counts": dict(categories),
            "order_count": len(orders),
        }

    run("expanded local dataset shape", local_shape)
    if not checks[-1]["passed"]:
        raise SystemExit(
            "Expanded dataset not ready; import 60 products and seed 30 orders first."
        )
    with httpx.Client(base_url=args.base_url, timeout=30) as client:

        def request(method, path, status=200, **kwargs):
            response = client.request(method, path, **kwargs)
            assert response.status_code == status
            if response.headers.get("content-type", "").startswith("application/json"):
                payload = response.json()
                identifier = payload.get(
                    "request_id", payload.get("error", {}).get("request_id")
                )
                assert str(uuid.UUID(identifier)) == identifier
                assert identifier == response.headers.get("x-request-id")
                assert "no-store" in response.headers.get("cache-control", "")
                assert private_keys_absent(payload)
                return payload
            return response

        def check_search(payload, mode, options=None):
            results = payload["results"]
            assert payload["query"]["mode"] == mode
            assert [row["rank"] for row in results] == list(range(1, len(results) + 1))
            ids = [row["product"]["product_id"] for row in results]
            assert len(set(ids)) == len(ids) and set(ids) <= by_id.keys()
            assert len(ids) <= payload["query"]["options"]["top_k"]
            scores = [row["score"] for row in results]
            assert all(math.isfinite(score) and -1 <= score <= 1 for score in scores)
            assert scores == sorted(scores, reverse=True)
            for row in results:
                assert row["product"] == public_summary(
                    by_id[row["product"]["product_id"]]
                )
                components = row["component_scores"]
                for component, present in (
                    ("text", mode != "image"),
                    ("image", mode in ("image", "multimodal")),
                ):
                    assert (components[component] is not None) == present
                    if present:
                        assert (
                            math.isfinite(components[component])
                            and -1 <= components[component] <= 1
                        )
            details = payload["meta"]
            assert [step["step"] for step in details["trace"]] == [
                "validation",
                "encoding",
                "retrieval",
                "filtering",
                "threshold",
                "ranking",
                "hydration",
            ]
            assert details["trace"][2]["output_count"] == 60
            assert details["trace"][-1]["output_count"] == len(results)
            assert all(
                math.isfinite(value) and value >= 0
                for value in details["timing_ms"].values()
            )
            for field in (
                "model_fingerprint",
                "index_fingerprint",
                "catalog_fingerprint",
            ):
                assert re.fullmatch(r"[a-f0-9]{64}", details[field])
            if meta:
                assert (
                    details["index_fingerprint"] == meta["index"]["index_fingerprint"]
                )
                assert (
                    details["catalog_fingerprint"]
                    == meta["index"]["catalog_fingerprint"]
                )
                assert (
                    details["model_fingerprint"] == meta["model"]["model_fingerprint"]
                )
            if options is not None:
                for key, value in options.items():
                    if key == "filters":
                        assert all(
                            payload["query"]["options"][key][field] == expected
                            for field, expected in value.items()
                        )
                    else:
                        assert payload["query"]["options"][key] == value
            return ids

        def capabilities():
            nonlocal meta
            request("GET", "/health/ready")
            meta = request("GET", "/api/v1/meta")
            assert (
                meta["index"]["product_count"] == 60
                and meta["model"]["dimension"] == 512
            )
            assert meta["capabilities"]["search"]["available"]
            assert meta["capabilities"]["orders"]["available"]
            assert set(meta["filters"]["categories"]) == set(CATEGORY_QUERIES)
            assert set(meta["filters"]["brands"]) == {
                product["brand"] for product in products
            }
            return {
                "index_fingerprint": meta["index"]["index_fingerprint"],
                "speech_configuration": meta["speech"]["configuration_state"],
            }

        run("ready expanded CPU model and capabilities", capabilities)
        sorted_products = sorted(products, key=lambda product: product["product_id"])
        for offset in (0, 20, 40, 60, 80):

            def page(offset=offset):
                payload = request("GET", f"/api/v1/products?offset={offset}&limit=20")
                assert (
                    payload["total"] == 60
                    and payload["offset"] == offset
                    and payload["limit"] == 20
                )
                assert payload["products"] == [
                    public_summary(product)
                    for product in sorted_products[offset : offset + 20]
                ]
                return {"offset": offset, "count": len(payload["products"])}

            run(f"catalog pagination offset {offset}", page)

        def credits():
            rows = request("GET", "/api/v1/credits")["credits"]
            assert (
                len(rows) == 60 and {row["product_id"] for row in rows} == by_id.keys()
            )
            for row in rows:
                asset = assets_by_id[row["asset_id"]]
                for field in ("source_page", "author", "license", "license_url"):
                    assert row[field] == asset[field]
            return {"count": len(rows)}

        run("all 60 public photo credits match provenance", credits)

        for product in sorted_products:
            product_id = product["product_id"]

            def detail(product=product):
                value = request("GET", f"/api/v1/products/{product['product_id']}")[
                    "product"
                ]
                assert {
                    key: value[key] for key in public_summary(product)
                } == public_summary(product)
                assert (
                    value["description"] == product["description"]
                    and value["stock_quantity"] == product["stock_quantity"]
                )
                asset = assets_by_id[product["image_asset_id"]]
                for field in ("source_page", "author", "license", "license_url"):
                    assert value["image_credit"][field] == asset[field]
                return {"product_id": product["product_id"]}

            run(f"product detail {product_id}", detail)

            def media(product=product):
                asset = assets_by_id[product["image_asset_id"]]
                local = ROOT / product["image_path"]
                assert local.resolve().is_relative_to((ROOT / "data/images").resolve())
                assert (
                    sha256(local) == asset["sha256"]
                    and local.stat().st_size == asset["bytes"]
                )
                assert (
                    asset["real_photo_review"] == "passed" and asset["review_evidence"]
                )
                response = request(
                    "GET", f"/api/v1/media/products/{product['product_id']}"
                )
                assert hashlib.sha256(response.content).hexdigest() == asset["sha256"]
                assert response.headers.get("x-content-type-options") == "nosniff"
                assert response.headers["etag"] == f'"{asset["sha256"]}"'
                cached = request(
                    "GET",
                    f"/api/v1/media/products/{product['product_id']}",
                    status=304,
                    headers={"If-None-Match": response.headers["etag"]},
                )
                assert cached.content == b""
                return {"product_id": product["product_id"], "sha256": asset["sha256"]}

            run(f"real photo bytes and ETag {product_id}", media)

        for category, query in CATEGORY_QUERIES.items():

            def filtered(category=category, query=query):
                filters = {"category": category}
                options = {"top_k": 20, "result_policy": "nearest", "filters": filters}
                payload = request(
                    "POST",
                    "/api/v1/search",
                    json={"mode": "text", "text": query, "options": options},
                )
                ids = check_search(payload, "text", options)
                assert set(ids) == expected_ids(products, filters)
                return {
                    "category": category,
                    "expected_ids": sorted(expected_ids(products, filters)),
                    "actual_ids": ids,
                }

            run(f"hard category full eligible set {category}", filtered)

            def combination(category=category, query=query):
                product = next(
                    product
                    for product in sorted_products
                    if product["category"] == category and product["stock_quantity"] > 0
                )
                filters = {
                    "category": category,
                    "brand": product["brand"],
                    "min_price": product["price_vnd"],
                    "max_price": product["price_vnd"],
                    "in_stock": True,
                }
                options = {"top_k": 20, "result_policy": "nearest", "filters": filters}
                payload = request(
                    "POST",
                    "/api/v1/search",
                    json={"mode": "text", "text": query, "options": options},
                )
                ids = check_search(payload, "text", options)
                assert set(ids) == expected_ids(products, filters)
                return {
                    "category": category,
                    "filters": filters,
                    "expected_ids": sorted(expected_ids(products, filters)),
                    "actual_ids": ids,
                }

            run(f"inclusive brand price stock combination {category}", combination)

            def probe(category=category, query=query):
                payload = request(
                    "POST",
                    "/api/v1/search",
                    json={
                        "mode": "text",
                        "text": query,
                        "options": {"top_k": 3, "result_policy": "nearest"},
                    },
                )
                ids = check_search(payload, "text")
                hit = any(
                    by_id[product_id]["category"] == category for product_id in ids
                )
                semantic.append(
                    {
                        "category": category,
                        "query": query,
                        "actual_ids": ids,
                        "actual_categories": [
                            by_id[product_id]["category"] for product_id in ids
                        ],
                        "category_hit_at_3": hit,
                        "scores": [row["score"] for row in payload["results"]],
                    }
                )
                return {"category_hit_at_3": hit}

            run(f"unfiltered Vietnamese category semantic probe {category}", probe)

            product = next(
                product
                for product in sorted_products
                if product["category"] == category
            )
            for mode in ("image", "multimodal"):

                def visual(mode=mode, product=product, category=category):
                    data = {
                        "options": json.dumps({"top_k": 3, "result_policy": "nearest"})
                    }
                    if mode == "multimodal":
                        data.update(text=product["name"], text_weight="0.5")
                    payload = request(
                        "POST",
                        f"/api/v1/search/{mode}",
                        files={
                            "image": (
                                "catalog.jpg",
                                (ROOT / product["image_path"]).read_bytes(),
                                "image/jpeg",
                            )
                        },
                        data=data,
                    )
                    ids = check_search(payload, mode)
                    alignment.append(
                        {
                            "mode": mode,
                            "category": category,
                            "source_product_id": product["product_id"],
                            "actual_ids": ids,
                            "self_hit_at_3": product["product_id"] in ids,
                        }
                    )
                    return {"category": category, "actual_ids": ids}

                run(f"catalog-photo alignment smoke {mode} {category}", visual)

        def voice():
            payload = request(
                "POST",
                "/api/v1/search",
                json={
                    "mode": "voice",
                    "voice_source": "manual_transcript",
                    "text": "tôi muốn tìm kính mát",
                    "options": {"top_k": 3},
                },
            )
            ids = check_search(payload, "voice")
            assert payload["query"]["voice_source"] == "manual_transcript"
            return {"actual_ids": ids, "provenance": "manual_transcript_not_azure"}

        run("manual voice transcript shares real multilingual encoder", voice)

        def empty_filters():
            payload = request(
                "POST",
                "/api/v1/search",
                json={
                    "mode": "text",
                    "text": "thời trang",
                    "options": {"filters": {"max_price": 0}},
                },
            )
            assert (
                check_search(payload, "text") == []
                and payload["meta"]["empty_reason"] == "filters"
            )

        run("filters remove all candidates without errors", empty_filters)

        for order in orders:
            order_id = order["order_id"]
            owned = order["customer_id"] == "C001"
            for kind in ("summary", "detail"):

                def order_check(order=order, owned=owned, kind=kind):
                    path = (
                        f"/api/v1/orders?order_id={order['order_id'].lower()}"
                        if kind == "summary"
                        else f"/api/v1/orders/{order['order_id']}"
                    )
                    result = request("GET", path, status=200 if owned else 404)
                    if owned:
                        expected = {
                            key: value
                            for key, value in order.items()
                            if key != "customer_id"
                            and (kind != "summary" or key != "items")
                        }
                        assert result["order"] == expected
                        assert order["total_vnd"] == sum(
                            item["quantity"] * item["unit_price_vnd"]
                            for item in order["items"]
                        )
                    else:
                        missing_path = (
                            "/api/v1/orders?order_id=O999"
                            if kind == "summary"
                            else "/api/v1/orders/O999"
                        )
                        missing = request("GET", missing_path, status=404)
                        assert (
                            result["error"]["code"]
                            == missing["error"]["code"]
                            == "ORDER_NOT_FOUND"
                        )
                        assert result["error"]["message"] == missing["error"]["message"]
                        assert set(result) == {"error"}
                    return {
                        "order_id": order["order_id"],
                        "expected_status": 200 if owned else 404,
                    }

                run(f"order {kind} privacy and snapshot {order_id}", order_check)

        boundaries = [
            (
                "unknown category",
                {
                    "mode": "text",
                    "text": "giày",
                    "options": {"filters": {"category": "television"}},
                },
            ),
            (
                "unknown brand",
                {
                    "mode": "text",
                    "text": "giày",
                    "options": {"filters": {"brand": "__unknown_brand__"}},
                },
            ),
            (
                "inverted price bounds",
                {
                    "mode": "text",
                    "text": "giày",
                    "options": {"filters": {"min_price": 100, "max_price": 99}},
                },
            ),
            ("top-k 0", {"mode": "text", "text": "giày", "options": {"top_k": 0}}),
            ("top-k 21", {"mode": "text", "text": "giày", "options": {"top_k": 21}}),
            (
                "boolean top-k",
                {"mode": "text", "text": "giày", "options": {"top_k": True}},
            ),
            ("empty text", {"mode": "text", "text": " "}),
            ("too long text", {"mode": "text", "text": "a" * 501}),
            (
                "client owner field",
                {"mode": "text", "text": "giày", "customer_id": "C002"},
            ),
        ]
        for name, body in boundaries:
            run(
                f"boundary {name}",
                lambda body=body: {
                    "status": request("POST", "/api/v1/search", status=422, json=body)[
                        "error"
                    ]["code"]
                },
            )
        for path in (
            "/api/v1/products?limit=0",
            "/api/v1/products?offset=-1",
            "/api/v1/products?limit=1&limit=2",
            "/api/v1/orders?order_id=O002&customer_id=C002",
            "/api/v1/media/products/P001?retry=1",
        ):
            run(
                f"strict query {path}",
                lambda path=path: {
                    "error_code": request("GET", path, status=422)["error"]["code"]
                },
            )
        run(
            "client customer header rejected",
            lambda: {
                "error_code": request(
                    "GET",
                    "/api/v1/products",
                    status=422,
                    headers={"X-Customer-ID": "C002"},
                )["error"]["code"]
            },
        )
        run(
            "missing product returns typed 404",
            lambda: {
                "error_code": request("GET", "/api/v1/products/P999", status=404)[
                    "error"
                ]["code"]
            },
        )
        run(
            "malformed image rejected before encoder",
            lambda: {
                "error_code": request(
                    "POST",
                    "/api/v1/search/image",
                    status=422,
                    files={
                        "image": ("broken.jpg", b"\xff\xd8\xffinvalid", "image/jpeg")
                    },
                )["error"]["code"]
            },
        )

        for mode in ("text", "image", "multimodal"):

            def policy_probe(mode=mode):
                assert mode in meta.get("capabilities", {}).get("relevant", {}).get(
                    "modes", []
                )
                options = {"top_k": 3, "result_policy": "relevant"}
                if mode == "text":
                    payload = request(
                        "POST",
                        "/api/v1/search",
                        json={
                            "mode": "text",
                            "text": "bánh pizza cà chua và phô mai",
                            "options": options,
                        },
                    )
                else:
                    data = {"options": json.dumps(options)}
                    if mode == "multimodal":
                        data.update(
                            text="bánh pizza cà chua và phô mai", text_weight="0.5"
                        )
                    payload = request(
                        "POST",
                        f"/api/v1/search/{mode}",
                        files={
                            "image": (
                                "pizza.jpg",
                                (ROOT / "data/queries/Q001.jpg").read_bytes(),
                                "image/jpeg",
                            )
                        },
                        data=data,
                    )
                ids = check_search(payload, mode, options)
                assert payload["meta"]["threshold"] is not None and re.fullmatch(
                    r"[a-f0-9]{64}", payload["meta"]["policy_fingerprint"]
                )
                ood.append(
                    {
                        "mode": mode,
                        "actual_ids": ids,
                        "rejected": not ids,
                        "threshold": payload["meta"]["threshold"],
                        "empty_reason": payload["meta"]["empty_reason"],
                        "scope": "existing_calibration_smoke_not_frozen_test",
                    }
                )
                return {"actual_ids": ids, "rejected": not ids}

            run(f"fresh relevant policy OOD observation {mode}", policy_probe)
        run(
            "backend ready after all expanded checks",
            lambda: request("GET", "/health/ready") and {},
        )

    report = {
        "status": "passed" if all(check["passed"] for check in checks) else "failed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command": f"python scripts/verify_expanded_demo.py --base-url {args.base_url}",
        "code_commit": commit_hash(),
        "azure_live_called": False,
        "scope": "actual HTTP + real CPU encoder; semantic probes use nearest; photo reuse is alignment smoke",
        "products_sha256": sha256(ROOT / "data/products.json"),
        "orders_sha256": sha256(ROOT / "data/orders.json"),
        "manifest_sha256": sha256(ROOT / "data/image_sources.json"),
        "requirements_lock_sha256": sha256(ROOT / "backend/requirements.lock.txt"),
        "verification_script_sha256": sha256(Path(__file__)),
        "model": meta.get("model"),
        "index": meta.get("index"),
        "speech": meta.get("speech"),
        "check_count": len(checks),
        "passed_count": sum(check["passed"] for check in checks),
        "failed_count": sum(not check["passed"] for check in checks),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "checks": checks,
        "semantic_category_probes": {
            "case_count": len(semantic),
            "category_hits_at_3": sum(case["category_hit_at_3"] for case in semantic),
            "category_hit_at_3": sum(case["category_hit_at_3"] for case in semantic)
            / len(semantic)
            if semantic
            else None,
            "scope": "12 catalog-derived category smoke cases, not independent held-out relevance evidence",
            "cases": semantic,
        },
        "catalog_photo_alignment": alignment,
        "ood_observations": ood,
        "remaining_external_gate": "Azure vi-VN recognition is not exercised by this command",
    }
    target = ROOT / "artifacts/backend/expanded-demo.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "check_count",
                    "passed_count",
                    "failed_count",
                    "duration_seconds",
                    "semantic_category_probes",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
