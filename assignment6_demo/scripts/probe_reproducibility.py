"""Record a stable search snapshot; compare after two operator-controlled restarts."""

import argparse
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, choices=(0, 1, 2), required=True)
    args = parser.parse_args()
    path = ROOT / "artifacts/backend/reproducibility.json"
    report = {"scope": "same nearest queries across two manually verified local backend restarts",
              "tolerance": 1e-5, "runs": [], "passed": False}
    if args.run:
        report = json.loads(path.read_text(encoding="utf-8"))
    if len(report["runs"]) != args.run:
        raise ValueError("Run sequence must be baseline, restart 1, restart 2")
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        client.get("/health/ready").raise_for_status()
        meta = client.get("/api/v1/meta").json()
        results = []
        for text in ("giày Converse đỏ cổ cao", "túi da màu nâu", "đồng hồ mặt trắng"):
            response = client.post("/api/v1/search", json={"mode": "text", "text": text})
            response.raise_for_status()
            body = response.json()
            results.append({"mode": "text", "text": text,
                            "ranking": [{"id": r["product"]["product_id"], "score": r["score"]} for r in body["results"]]})
        for endpoint in ("image", "multimodal"):
            data = {"text": "giày chạy bộ màu đen", "text_weight": "0.5"} if endpoint == "multimodal" else {}
            with (ROOT / "data/images/P001.jpg").open("rb") as image:
                response = client.post(f"/api/v1/search/{endpoint}", files={"image": ("fixture.jpg", image, "image/jpeg")}, data=data)
            response.raise_for_status()
            results.append({"mode": endpoint, "ranking": [{"id": r["product"]["product_id"], "score": r["score"]}
                                                             for r in response.json()["results"]]})
    snapshot = {"run": args.run, "model": meta["model"], "index": meta["index"], "results": results}
    if args.run:
        baseline = report["runs"][0]
        assert snapshot["model"] == baseline["model"] and snapshot["index"] == baseline["index"]
        for current, previous in zip(results, baseline["results"], strict=True):
            assert current["mode"] == previous["mode"]
            for actual, expected in zip(current["ranking"], previous["ranking"], strict=True):
                assert actual["id"] == expected["id"] and abs(actual["score"] - expected["score"]) <= 1e-5
    report["runs"].append(snapshot)
    report["passed"] = len(report["runs"]) == 3
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run": args.run, "runs_recorded": len(report["runs"]), "passed": report["passed"]}))


if __name__ == "__main__":
    main()
