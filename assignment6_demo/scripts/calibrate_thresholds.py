"""Fit separate relevance thresholds using real local embeddings and demo labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def collect(root: Path, cases: list[dict]) -> tuple[list[dict], str, str]:
    from app.application.embedding_service import AIEmbeddingService
    from app.data.vector_index import VectorIndex
    from app.data.product_repository import ProductRepository
    from app.application.query_service import QueryService
    from app.application.search_service import SearchService
    from app.domain import SearchOptions

    repo = ProductRepository(root)
    encoder = AIEmbeddingService(root)
    index = VectorIndex(root, repo.products, encoder.model_fingerprint)
    if not encoder.available or not index.available:
        raise SystemExit("Model/index chưa sẵn sàng. Chạy download_models.py rồi build_index.py.")
    query_service = QueryService(encoder)
    service = SearchService(repo, encoder, index, root)
    records = []
    for case in cases:
        options = SearchOptions(top_k=20, result_policy="nearest", filters=case.get("filters", {}))
        mode = case["mode"]
        if mode == "text":
            query = query_service.build_text("text", case["text"], options)
        else:
            path = (root / case["image_path"]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Query image must stay inside demo root")
            content = path.read_bytes()
            if mode == "image":
                query = query_service.build_image(content, options, content_type="image/jpeg")
            else:
                query = query_service.build_multimodal(
                    case["text"], content, options, text_weight=case["text_weight"], content_type="image/jpeg"
                )
        response = service.search(query)
        ranking = [
            {"product_id": item["product"]["product_id"], "score": item["score"]} for item in response["results"]
        ]
        records.append({**case, "ranking": ranking})
        print(f"Encoded {case['query_id']}: {ranking[0]['product_id'] if ranking else 'empty'}", flush=True)
    return records, index.fingerprint, encoder.model_fingerprint


def metrics(records: list[dict], threshold: float) -> dict:
    positive = [r for r in records if not r["is_ood"]]
    ood = [r for r in records if r["is_ood"]]
    hits = 0
    rejections = 0
    for record in records:
        selected = [r["product_id"] for r in record["ranking"] if r["score"] >= threshold][:3]
        if record["is_ood"]:
            rejections += not selected
        else:
            hits += bool(set(selected).intersection(record["expected_product_ids"]))
    return {
        "positive_count": len(positive),
        "ood_count": len(ood),
        "hit_at_3_count": hits,
        "ood_rejection_count": rejections,
        "positive_hit_at_3": hits / len(positive) if positive else None,
        "ood_rejection_rate": rejections / len(ood) if ood else None,
    }


def choose(records: list[dict]) -> dict | None:
    if not any(r["is_ood"] for r in records) or not any(not r["is_ood"] for r in records):
        return None
    observed = sorted({r["score"] for record in records for r in record["ranking"]})
    candidates = {-1.0, 1.0, *observed}
    candidates.update((left + right) / 2 for left, right in zip(observed, observed[1:]))
    feasible = []
    for threshold in sorted(candidates):
        result = metrics(records, threshold)
        if result["positive_hit_at_3"] >= 0.8 and result["ood_rejection_rate"] >= 0.6:
            feasible.append({"threshold": threshold, "metrics": result})
    return min(feasible, key=lambda p: (-p["metrics"]["positive_hit_at_3"], p["threshold"])) if feasible else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    fixture_path = root / "evaluation/queries.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = [case for case in fixture["queries"] if case["split"] == "calibration"]
    records, index_fp, model_fp = collect(root, cases)
    policies = []
    unavailable = []
    for mode in ("text", "image", "multimodal"):
        subset = [record for record in records if record["mode"] == mode]
        selected = choose(subset)
        if selected is None:
            unavailable.append(mode)
        else:
            policies.append(
                {
                    "mode": mode,
                    "text_weight": 0.5 if mode == "multimodal" else None,
                    **selected,
                    "evidence_scope": "small_demo_calibration_not_independent_test",
                }
            )
    policy = {
        "schema_version": 1,
        "index_fingerprint": index_fp,
        "model_fingerprint": model_fp,
        "scoring_version": "cosine_fusion_v1",
        "policies": policies,
        "calibration_split_sha256": canonical_hash(cases),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    policy["fingerprint"] = canonical_hash(policy)
    directory = root / "runtime/policies"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"relevance_{index_fp}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    report = {
        "scope": fixture["purpose"],
        "independent_quality_verified": False,
        "policy": policy,
        "unavailable_modes": unavailable,
        "queries": records,
    }
    evidence = root / "artifacts/backend/calibration.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "policy_file": str(path),
                "available_modes": [p["mode"] for p in policies],
                "unavailable_modes": unavailable,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if unavailable:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
