"""Measure warm, sequential real-CPU HTTP search latency, without Azure calls.

Default: one unmeasured warm-up + 30 measured requests for each of text, image,
multimodal. Failures are retained in the report and make the benchmark fail.
Cold process/model startup is intentionally not inferred from warm timings.
"""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import time
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], percent: float) -> float | None:
    """Linear interpolation of all successful latency samples, no trimming."""
    if not values:
        return None
    ordered = sorted(values)
    location = (len(ordered) - 1) * percent / 100
    lower = math.floor(location)
    upper = math.ceil(location)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (location - lower)


def hardware() -> dict:
    memory = None
    if platform.system() == "Windows":

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_pagefile", ctypes.c_ulonglong),
                ("available_pagefile", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            memory = status.total_physical
    packages = {}
    for package in (
        "torch",
        "transformers",
        "sentence-transformers",
        "numpy",
        "httpx",
        "fastapi",
    ):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    return {
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "physical_memory_bytes": memory,
        "python_version": platform.python_version(),
        "packages": packages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests-per-mode", type=int, default=30)
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
    if not 30 <= args.requests_per_mode <= 100:
        parser.error(
            "Use 30–100 measured requests per mode; the acceptance baseline is 30."
        )
    products_path = ROOT / "data/products.json"
    products = json.loads(products_path.read_text(encoding="utf-8"))
    if len(products) != 60:
        raise SystemExit("Import the 60-product catalog before benchmarking.")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    commit = commit if re.fullmatch(r"[a-f0-9]{40}", commit) else None
    results: dict = {}
    started = time.perf_counter()
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        ready = client.get("/health/ready")
        ready.raise_for_status()
        meta_response = client.get("/api/v1/meta")
        meta_response.raise_for_status()
        meta = meta_response.json()
        if (
            meta["index"]["product_count"] != 60
            or not meta["capabilities"]["search"]["available"]
        ):
            raise SystemExit(
                "Restart the backend with the expanded index before benchmarking."
            )
        options = {"top_k": 5, "result_policy": "nearest"}

        def invoke(mode, product):
            # Prepare bytes outside the request timer; measured HTTP still includes upload.
            image = (
                (ROOT / product["image_path"]).read_bytes() if mode != "text" else None
            )
            begin = time.perf_counter()
            sample = {
                "source_product_id": product["product_id"],
                "category": product["category"],
            }
            try:
                if mode == "text":
                    response = client.post(
                        "/api/v1/search",
                        json={
                            "mode": "text",
                            "text": product["name"],
                            "options": options,
                        },
                    )
                else:
                    fields = {"options": json.dumps(options)}
                    if mode == "multimodal":
                        fields.update(text=product["name"], text_weight="0.5")
                    response = client.post(
                        f"/api/v1/search/{mode}",
                        files={"image": ("catalog.jpg", image, "image/jpeg")},
                        data=fields,
                    )
                sample["http_status"] = response.status_code
                sample["wall_ms"] = (time.perf_counter() - begin) * 1000
                payload = response.json()
                if response.status_code != 200:
                    sample.update(
                        passed=False,
                        error_code=payload.get("error", {}).get("code", "HTTP_ERROR"),
                    )
                    return sample
                assert payload["query"]["mode"] == mode
                assert (
                    payload["meta"]["index_fingerprint"]
                    == meta["index"]["index_fingerprint"]
                )
                assert (
                    payload["meta"]["model_fingerprint"]
                    == meta["model"]["model_fingerprint"]
                )
                assert (
                    payload["meta"]["catalog_fingerprint"]
                    == meta["index"]["catalog_fingerprint"]
                )
                assert payload["meta"]["trace"][2]["output_count"] == 60
                assert 1 <= len(payload["results"]) <= 5
                assert all(math.isfinite(row["score"]) for row in payload["results"])
                sample.update(
                    passed=True,
                    request_id=payload["request_id"],
                    server_ms=payload["meta"]["timing_ms"]["total"],
                    actual_ids=[
                        row["product"]["product_id"] for row in payload["results"]
                    ],
                )
            except (httpx.HTTPError, ValueError, KeyError, AssertionError) as exc:
                sample.update(
                    passed=False,
                    wall_ms=(time.perf_counter() - begin) * 1000,
                    error_type=type(exc).__name__,
                )
            return sample

        for mode in ("text", "image", "multimodal"):
            warmup = invoke(mode, products[0])
            samples = []
            for number in range(args.requests_per_mode):
                # Distribute samples across all categories rather than repeat one query.
                product = products[(number * 7) % len(products)]
                samples.append({"number": number + 1, **invoke(mode, product)})
            successful = [sample["wall_ms"] for sample in samples if sample["passed"]]
            all_wall = [sample["wall_ms"] for sample in samples]
            p95 = percentile(successful, 95)
            failures = sum(not sample["passed"] for sample in samples)
            results[mode] = {
                "request_count": len(samples),
                "successful_count": len(successful),
                "failure_count": failures,
                "warmup": warmup,
                "wall_ms_successful": {
                    "min": min(successful) if successful else None,
                    "mean": statistics.fmean(successful) if successful else None,
                    "p50": percentile(successful, 50),
                    "p95": p95,
                    "p99": percentile(successful, 99),
                    "max": max(successful) if successful else None,
                },
                "wall_ms_all_requests": {
                    "p95": percentile(all_wall, 95),
                    "max": max(all_wall),
                },
                "server_ms_successful": {
                    "p95": percentile(
                        [sample["server_ms"] for sample in samples if sample["passed"]],
                        95,
                    )
                },
                "p95_target_ms": 5000,
                "passed": warmup["passed"]
                and failures == 0
                and p95 is not None
                and p95 <= 5000,
                "samples": samples,
            }
            print(
                json.dumps(
                    {
                        "mode": mode,
                        "samples": len(samples),
                        "errors": failures,
                        "p95_ms": p95,
                        "passed": results[mode]["passed"],
                    }
                ),
                flush=True,
            )
        final_meta = client.get("/api/v1/meta")
        final_meta.raise_for_status()
        stable_snapshot = final_meta.json()["index"] == meta["index"]

    report = {
        "status": "passed"
        if stable_snapshot and all(result["passed"] for result in results.values())
        else "failed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command": f"python scripts/benchmark_backend.py --requests-per-mode {args.requests_per_mode} --base-url {args.base_url}",
        "code_commit": commit,
        "hardware": hardware(),
        "models": meta["model"],
        "index": meta["index"],
        "products_sha256": hashlib.sha256(products_path.read_bytes()).hexdigest(),
        "requirements_lock_sha256": hashlib.sha256(
            (ROOT / "backend/requirements.lock.txt").read_bytes()
        ).hexdigest(),
        "benchmark_script_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "execution": "sequential HTTP on localhost; actual CPU encoders; nearest top_k=5; no concurrent QA during run",
        "snapshot_stable": stable_snapshot,
        "measured_request_count": sum(
            result["request_count"] for result in results.values()
        ),
        "unmeasured_warmup_request_count": 3,
        "cold_start": {
            "status": "not_measured",
            "reason": "Existing backend process was already loaded; no restart included in this benchmark",
        },
        "azure_live_called": False,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "percentile_method": "linear interpolation at (N-1)*p/100; no outlier removal; errors retained separately and fail the gate",
        "modes": results,
        "limitations": [
            "Measures this local hardware and catalog, not production capacity",
            "Photo queries reuse catalog assets for performance only, not a held-out relevance claim",
            "Includes HTTP serialization, upload and server queue/inference; excludes microphone recording, file read and Azure transcription",
        ],
    }
    target = ROOT / "artifacts/backend/performance.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "measured_request_count": report["measured_request_count"],
                "snapshot_stable": stable_snapshot,
                "duration_seconds": report["duration_seconds"],
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
