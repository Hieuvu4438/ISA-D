"""Live CPU encoder checks after allocating demo P041-M; no speech calls."""
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = "http://127.0.0.1:8000"
    session = requests.Session()
    response = session.get(base + "/api/v1/products/P041", timeout=30)
    response.raise_for_status()
    product = response.json()["product"]
    if not any(v["size"] == "M" and v["stock_quantity"] > 0 for v in product["variants"]):
        raise SystemExit("Precondition: allocate demo P041-M stock with the administrator UI first")
    photo = (ROOT / "data/images/P041.jpg").read_bytes()
    rows = []
    for strategy in ("semantic", "hybrid"):
        for mode in ("text", "voice", "image", "multimodal"):
            baseline = {}
            for size in (None, "M", "XS"):
                filters = {"category": "t_shirt", "in_stock": True}
                if size:
                    filters["size"] = size
                options = {"top_k": 20, "search_strategy": strategy, "filters": filters}
                if mode in ("text", "voice"):
                    payload = {"mode": mode, "text": "áo thun", "options": options}
                    if mode == "voice":
                        payload["voice_source"] = "manual_transcript"
                    result = session.post(base + "/api/v1/search", json=payload, timeout=30)
                else:
                    data = {"options": json.dumps(options)}
                    if mode == "multimodal":
                        data.update(text="áo thun", text_weight="0.5")
                    result = session.post(base + f"/api/v1/search/{mode}", data=data, files={"image": ("query.jpg", photo, "image/jpeg")}, timeout=30)
                body = result.json()
                results = body.get("results", [])
                passed = result.status_code == 200 and bool(body.get("meta", {}).get("model_fingerprint"))
                if size is None:
                    baseline = {r["product"]["product_id"]: r["score"] for r in results}
                    passed = passed and "P041" in baseline
                elif size == "M":
                    passed = passed and bool(results) and all("M" in r["product"].get("available_sizes", []) and abs(r["score"] - baseline.get(r["product"]["product_id"], float("inf"))) < 1e-6 for r in results)
                else:
                    passed = passed and not results and body.get("meta", {}).get("empty_reason") == "filters"
                rows.append({"mode": mode, "strategy": strategy, "size": size, "passed": passed, "status": result.status_code, "response": body})
    report = {"scope": "Exploratory hard size/stock filter and unchanged cosine checks with real CPU encoder, not independent relevance quality",
              "speech_calls": 0, "voice_evidence": "manual transcript only", "checks": len(rows), "passed": all(row["passed"] for row in rows),
              "query_image_sha256": hashlib.sha256(photo).hexdigest(), "product_snapshot": product, "rows": rows}
    (ROOT / "artifacts/backend/variants-real-encoder.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks": len(rows), "passed": report["passed"], "speech_calls": 0}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
