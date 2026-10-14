"""Real HTTP/model comparison for E2; no STT calls or model mocks."""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    raw = (ROOT / "evaluation/search_expansion.json").read_bytes()
    fixture = json.loads(raw)
    session = requests.Session()
    ready = session.get(args.base_url + "/health/ready", timeout=30)
    ready.raise_for_status()
    results = []
    for case in fixture["queries"]:
        for strategy in ("semantic", "hybrid"):
            started = perf_counter()
            response = session.post(args.base_url + "/api/v1/search", json={"mode": "text", "text": case["text"],
                "options": {"top_k": 3, "search_strategy": strategy}}, timeout=30)
            response.raise_for_status()
            body = response.json()
            results.append({**case, "strategy": strategy, "hit_at_3": any(row["product"]["category"] == case["category"] for row in body["results"]),
                            "elapsed_ms": (perf_counter() - started) * 1000, "response": body})
    metrics = {}
    for strategy in ("semantic", "hybrid"):
        metrics[strategy] = {}
        for family in ("standard", "variant"):
            rows = [row for row in results if row["strategy"] == strategy and row["family"] == family]
            metrics[strategy][family] = {"hits": sum(row["hit_at_3"] for row in rows), "total": len(rows),
                                        "hit_at_3": sum(row["hit_at_3"] for row in rows) / len(rows)}
    mechanics = []
    photo = (ROOT / "data/images/P001.jpg").read_bytes()
    for mode in ("image", "multimodal"):
        data = {"options": json.dumps({"top_k": 3, "search_strategy": "hybrid", "filters": {"in_stock": True}})}
        if mode == "multimodal":
            data.update(text="giày chạy bộ màu đen", text_weight="0.5")
        response = session.post(args.base_url + f"/api/v1/search/{mode}", data=data,
                                files={"image": ("P001.jpg", photo, "image/jpeg")}, timeout=30)
        response.raise_for_status()
        body = response.json()
        passed = bool(body["results"]) and all(-1 <= row["score"] <= 1 and row["product"]["in_stock"] for row in body["results"])
        mechanics.append({"mode": mode, "scope": "real catalog photo upload mechanics; same-image query, not independent relevance", "passed": passed, "response": body})
    report = {"scope": fixture["purpose"], "fixture_sha256": hashlib.sha256(raw).hexdigest(),
              "model_fingerprint": results[0]["response"]["meta"]["model_fingerprint"],
              "index_fingerprint": results[0]["response"]["meta"]["index_fingerprint"],
              "cpu": True, "mocked_encoder": False, "requests": len(results) + len(mechanics), "metrics": metrics,
              "passed": all(group["hit_at_3"] >= .8 for group in metrics["hybrid"].values()) and all(row["passed"] for row in mechanics),
              "independent_full_quality_verified": False, "ood_rejection_verified": False, "queries": results, "multimodal_mechanics": mechanics}
    target = ROOT / "artifacts/backend/search-expansion-real-model.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("queries", "multimodal_mechanics")}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
