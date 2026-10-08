"""Recheck demo fixtures against the saved policy; this is not a held-out benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from calibrate_thresholds import ROOT, canonical_hash, collect, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    fixture = json.loads((root / "evaluation/queries.json").read_text(encoding="utf-8"))
    records, index_fp, model_fp = collect(root, fixture["queries"])
    policy = json.loads((root / f"runtime/policies/relevance_{index_fp}.json").read_text(encoding="utf-8"))
    fingerprint = policy.pop("fingerprint")
    if canonical_hash(policy) != fingerprint or policy["model_fingerprint"] != model_fp:
        raise ValueError("Policy fingerprint/model mismatch; recalibrate")
    results = []
    for p in policy["policies"]:
        subset = [record for record in records if record["mode"] == p["mode"]]
        actual = metrics(subset, p["threshold"])
        passed = actual["positive_hit_at_3"] >= 0.8 and actual["ood_rejection_rate"] >= 0.6
        results.append({"mode": p["mode"], "threshold": p["threshold"], "metrics": actual, "passed": passed})
    report = {
        "scope": fixture["purpose"],
        "independent_quality_verified": False,
        "index_fingerprint": index_fp,
        "model_fingerprint": model_fp,
        "fixture_sha256": canonical_hash(fixture),
        "modes": results,
        "queries": records,
        "passed": len(results) == 3 and all(result["passed"] for result in results),
    }
    target = root / "artifacts/backend/demo-evaluation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "queries"}, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
