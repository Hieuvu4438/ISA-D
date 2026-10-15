"""Real local encoder/API price-constraint checks; no speech provider calls."""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("áo thun dưới 1 triệu", None, 999999),
    ("ao phong khong qua 1,5tr", None, 1500000),
    ("áo thun từ 500 nghìn đến 1,5 triệu", 500000, 1500000),
    ("áo thun trên 500k dưới 1tr", 500001, 999999),
    ("áo thun không dưới 500k", 500000, None),
    ("áo thun dưới 1 triệu rưỡi", None, 1499999),
    ("áo thun dưới 1tr500k", None, 1499999),
    ("t-shirt under 1 million", None, 999999),
    ("t-shirt at most 500 thousand", None, 500000),
    ("áo thun ≤1tr", None, 1000000),
    ("áo thun dưới một triệu", None, 999999),
    ("áo thun từ năm trăm nghìn đến một triệu", 500000, 1000000),
    ("áo thun dưới một triệu rưỡi", None, 1499999),
]
INVALID = [
    ("áo thun khoảng 1tr", "PRICE_QUERY_AMBIGUOUS"),
    ("áo từ 2tr đến 1tr", "PRICE_QUERY_CONFLICT"),
    ("áo dưới 1tr hoặc trên 2tr", "PRICE_QUERY_AMBIGUOUS"),
    ("áo dưới 100USD", "PRICE_CURRENCY_UNSUPPORTED"),
    ("áo dưới 1.500 triệu", "PRICE_QUERY_AMBIGUOUS"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1") or parsed.username or parsed.password:
        parser.error("Use the local HTTP application server without credentials in its URL")
    base = args.base_url.rstrip("/")
    session = requests.Session()
    session.get(base + "/health/ready", timeout=30).raise_for_status()
    rows = []
    for strategy in ("semantic", "hybrid"):
        for text, lower, upper in CASES:
            started = perf_counter()
            response = session.post(base + "/api/v1/search", json={"mode": "text", "text": text,
                "options": {"top_k": 20, "search_strategy": strategy, "filters": {"category": "t_shirt"}}}, timeout=30)
            body = response.json()
            plan = body.get("meta", {}).get("price_interpretation", {})
            results = body.get("results", [])
            passed = response.status_code == 200 and bool(results) and plan.get("applied") is True and plan.get("inferred_filters") == {"min_price": lower, "max_price": upper}
            passed = passed and all((lower is None or row["product"]["price_vnd"] >= lower) and (upper is None or row["product"]["price_vnd"] <= upper) for row in results)
            rows.append({"kind": "real_encoder_price_bound", "strategy": strategy, "text": text,
                         "expected": {"min_price": lower, "max_price": upper}, "status": response.status_code,
                         "passed": passed, "elapsed_ms": (perf_counter() - started) * 1000, "response": body})
    for text, code in INVALID:
        response = session.post(base + "/api/v1/search", json={"mode": "text", "text": text}, timeout=30)
        body = response.json()
        rows.append({"kind": "explicit_rejection", "text": text, "status": response.status_code,
                     "expected_code": code, "passed": response.status_code == 422 and body.get("error", {}).get("code") == code, "response": body})
    photo = (ROOT / "data/images/P001.jpg").read_bytes()
    text = "áo thun dưới 1 triệu"
    baseline = {}
    for mode in ("text", "voice", "multimodal", "image"):
        for enabled in (False, True):
            options = {"top_k": 20, "search_strategy": "hybrid", "interpret_price": enabled, "filters": {"category": "t_shirt"}}
            if mode in ("text", "voice"):
                payload = {"mode": mode, "text": text, "options": options}
                if mode == "voice":
                    payload["voice_source"] = "manual_transcript"
                response = session.post(base + "/api/v1/search", json=payload, timeout=30)
            else:
                data = {"options": json.dumps(options)}
                if mode == "multimodal":
                    data.update(text=text, text_weight="0.5")
                response = session.post(base + f"/api/v1/search/{mode}", data=data, files={"image": ("query.jpg", photo, "image/jpeg")}, timeout=30)
            body = response.json()
            results = body.get("results", [])
            passed = response.status_code == 200 and bool(results)
            if not enabled:
                baseline[mode] = {row["product"]["product_id"]: row["score"] for row in results}
            else:
                passed = passed and all(abs(row["score"] - baseline[mode].get(row["product"]["product_id"], float("inf"))) < 1e-6 for row in results)
                if mode != "image":
                    passed = passed and all(row["product"]["price_vnd"] < 1000000 for row in results)
                else:
                    passed = passed and body.get("meta", {}).get("price_interpretation", {}).get("applied") is False
            rows.append({"kind": "all_mode_cosine_invariant", "mode": mode, "interpret_price": enabled,
                         "status": response.status_code, "passed": passed, "response": body})
    report = {"scope": "Exploratory real CPU encoder/HTTP price constraint properties, not frozen independent Hit@K quality",
              "speech_calls": 0, "voice_evidence": "manual transcript search only; no STT/provider verification",
              "query_image_sha256": hashlib.sha256(photo).hexdigest(), "fixture_sha256": hashlib.sha256(json.dumps(CASES + INVALID, ensure_ascii=False).encode()).hexdigest(),
              "checks": len(rows), "passed": all(row["passed"] for row in rows), "rows": rows}
    (ROOT / "artifacts/backend/price-query-real-encoder.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks": len(rows), "passed": report["passed"], "failed": sum(not row["passed"] for row in rows), "speech_calls": 0}))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
