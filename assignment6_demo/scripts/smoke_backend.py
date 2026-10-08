"""Smoke the running demo API. Never calls paid Azure recognition."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    checks = []
    start = time.perf_counter()
    with httpx.Client(base_url=args.base_url, timeout=30) as client:

        def request(name, method, path, status=200, **kwargs):
            response = client.request(method, path, **kwargs)
            if response.status_code != status:
                raise AssertionError(f"{name}: expected {status}, got {response.status_code}; {response.text[:300]}")
            checks.append({"name": name, "status": response.status_code})
            if response.headers.get("content-type", "").startswith("application/json"):
                payload = response.json()
                identifier = payload.get("request_id", payload.get("error", {}).get("request_id"))
                assert identifier == response.headers.get("x-request-id"), name
                assert "customer_id" not in response.text and "local_path" not in response.text, name
                return payload
            return response

        def search_assert(payload):
            results = payload["results"]
            assert [r["rank"] for r in results] == list(range(1, len(results) + 1))
            assert len({r["product"]["product_id"] for r in results}) == len(results)
            assert all(math.isfinite(r["score"]) and -1 <= r["score"] <= 1 for r in results)
            assert [r["score"] for r in results] == sorted([r["score"] for r in results], reverse=True)
            assert [t["step"] for t in payload["meta"]["trace"]] == [
                "validation",
                "encoding",
                "retrieval",
                "filtering",
                "threshold",
                "ranking",
                "hydration",
            ]
            assert payload["meta"]["trace"][-1]["output_count"] == len(results)
            return results

        request("liveness", "GET", "/health/live")
        request("search readiness", "GET", "/health/ready")
        meta = request("capabilities", "GET", "/api/v1/meta")
        assert meta["model"]["dimension"] == 512 and meta["capabilities"]["search"]["available"]
        assert meta["speech"]["language"] == "vi-VN"
        products = request("catalog", "GET", "/api/v1/products")
        assert products["total"] == 12 and len(products["products"]) == 12
        assert request("catalog empty page", "GET", "/api/v1/products?offset=12")["products"] == []
        detail = request("product detail", "GET", "/api/v1/products/P001")
        assert detail["product"]["image_credit"]["source_page"].startswith("https://")
        credits = request("real-photo credits", "GET", "/api/v1/credits")
        assert len(credits["credits"]) == 12 and all(c["author"] and c["license"] for c in credits["credits"])
        image = request("local original media", "GET", "/api/v1/media/products/P001")
        assert (
            hashlib.sha256(image.content).hexdigest()
            == hashlib.sha256((root / "data/images/P001.jpg").read_bytes()).hexdigest()
        )
        payload = request(
            "Vietnamese text",
            "POST",
            "/api/v1/search",
            json={"mode": "text", "text": "giày Converse màu đỏ", "options": {"top_k": 3}},
        )
        assert "P006" in [r["product"]["product_id"] for r in search_assert(payload)]
        payload = request(
            "manual voice transcript",
            "POST",
            "/api/v1/search",
            json={"mode": "voice", "voice_source": "manual_transcript", "text": "túi da màu nâu"},
        )
        search_assert(payload)
        assert payload["query"]["voice_source"] == "manual_transcript"
        payload = request(
            "hard filters",
            "POST",
            "/api/v1/search",
            json={
                "mode": "text",
                "text": "giày đỏ",
                "options": {
                    "top_k": 20,
                    "filters": {"brand": "Converse", "min_price": 1100000, "max_price": 1100000, "in_stock": True},
                },
            },
        )
        assert [r["product"]["product_id"] for r in search_assert(payload)] == ["P006"]
        payload = request(
            "empty filters",
            "POST",
            "/api/v1/search",
            json={"mode": "text", "text": "giày", "options": {"filters": {"max_price": 0}}},
        )
        assert search_assert(payload) == [] and payload["meta"]["empty_reason"] == "filters"
        data = (root / "data/images/P001.jpg").read_bytes()
        files = {"image": ("photo.jpg", data, "image/jpeg")}
        payload = request("image upload search", "POST", "/api/v1/search/image", files=files)
        assert "P001" in [r["product"]["product_id"] for r in search_assert(payload)[:3]]
        payload = request(
            "multimodal weighted search",
            "POST",
            "/api/v1/search/multimodal",
            files=files,
            data={"text": "giày chạy bộ On màu đen", "text_weight": "0.5"},
        )
        assert "P001" in [r["product"]["product_id"] for r in search_assert(payload)[:3]]
        for mode in ("text", "image", "multimodal"):
            options = {"result_policy": "relevant", "top_k": 3}
            if mode == "text":
                payload = request(
                    "relevant text OOD empty",
                    "POST",
                    "/api/v1/search",
                    json={"mode": "text", "text": "bánh pizza cà chua và phô mai", "options": options},
                )
            else:
                files = {"image": ("pizza.jpg", (root / "data/queries/Q001.jpg").read_bytes(), "image/jpeg")}
                fields = {"options": json.dumps(options)}
                if mode == "multimodal":
                    fields.update(text="bánh pizza phô mai cà chua", text_weight="0.5")
                payload = request(
                    f"relevant {mode} OOD empty", "POST", f"/api/v1/search/{mode}", files=files, data=fields
                )
            assert search_assert(payload) == [] and payload["meta"]["empty_reason"] == "threshold"
        order = request("own order summary", "GET", "/api/v1/orders?order_id=o001")
        assert order["order"]["order_id"] == "O001"
        order = request("own order detail", "GET", "/api/v1/orders/O001")["order"]
        assert order["total_vnd"] == sum(i["quantity"] * i["unit_price_vnd"] for i in order["items"])
        request("second own order", "GET", "/api/v1/orders/O003")
        foreign = request("foreign order hidden", "GET", "/api/v1/orders/O002", status=404)
        missing = request("missing order", "GET", "/api/v1/orders/O999", status=404)
        assert foreign["error"]["code"] == missing["error"]["code"] == "ORDER_NOT_FOUND"
        assert foreign["error"]["message"] == missing["error"]["message"]
        request("customer header forbidden", "GET", "/api/v1/products", status=422, headers={"X-Customer-ID": "C002"})
        request("customer query forbidden", "GET", "/api/v1/orders?order_id=O002&customer_id=C002", status=422)
        request(
            "strict invalid top-k",
            "POST",
            "/api/v1/search",
            status=422,
            json={"mode": "text", "text": "giày", "options": {"top_k": True}},
        )
        request(
            "invalid bounds",
            "POST",
            "/api/v1/search",
            status=422,
            json={"mode": "text", "text": "giày", "options": {"filters": {"min_price": 200, "max_price": 100}}},
        )
        request(
            "malformed JSON",
            "POST",
            "/api/v1/search",
            status=400,
            content=b'{"mode":',
            headers={"Content-Type": "application/json"},
        )
        request(
            "duplicate JSON fields",
            "POST",
            "/api/v1/search",
            status=400,
            content=b'{"mode":"text","mode":"voice","text":"shoe"}',
            headers={"Content-Type": "application/json"},
        )
        request(
            "fake JPEG rejected",
            "POST",
            "/api/v1/search/image",
            status=422,
            files={"image": ("fake.jpg", b"\xff\xd8\xffinvalid-image-bytes", "image/jpeg")},
        )
        request(
            "invalid WAV rejected before Azure",
            "POST",
            "/api/v1/speech/transcriptions",
            status=422,
            files={"audio": ("fake.wav", b"RIFF\x00\x00\x00\x00WAVEbroken", "audio/wav")},
        )
    report = {
        "status": "passed",
        "base_url": args.base_url,
        "check_count": len(checks),
        "checks": checks,
        "duration_seconds": round(time.perf_counter() - start, 3),
        "azure_live_called": False,
        "index_fingerprint": meta["index"]["index_fingerprint"],
    }
    target = root / "artifacts/backend/http-smoke.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "checks"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
