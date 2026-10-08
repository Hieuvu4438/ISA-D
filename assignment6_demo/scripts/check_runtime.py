"""Check a restarted backend, malformed inputs and unconfigured speech; no paid calls."""

import io
import json
import wave
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=20) as client:

        def check(name, response, expected):
            data = response.json() if "application/json" in response.headers.get("content-type", "") else {}
            checks.append(
                {
                    "name": name,
                    "actual_status": response.status_code,
                    "expected_status": expected,
                    "passed": response.status_code in expected
                    if isinstance(expected, list)
                    else response.status_code == expected,
                    "error_code": data.get("error", {}).get("code"),
                }
            )

        for path in ["/health/ready", "/docs", "/openapi.json"]:
            check(path, client.get(path), 200)
        headers = {"Content-Type": "application/json"}
        bodies = [
            ("deeply nested JSON", "[" * 1200 + "]" * 1200, [400, 422]),
            ("overflow JSON float", '{"mode":"text","text":"giày","options":{"top_k":1e999}}', 400),
            ("invalid Unicode escape", '{"mode":"text","text":"\\ud800"}', 400),
            ("invalid JSON object", "[]", 422),
        ]
        for name, body, status in bodies:
            check(name, client.post("/api/v1/search", content=body.encode("utf-8"), headers=headers), status)
        check("real tokenizer limit", client.post("/api/v1/search", json={"mode": "text", "text": "ạ " * 140}), 422)
        check("oversized JSON envelope", client.post("/api/v1/search", content=b" " * 17000, headers=headers), 413)
        check(
            "unsupported request type",
            client.post("/api/v1/search", content="text", headers={"Content-Type": "text/plain"}),
            415,
        )
        check("wrong method", client.post("/api/v1/products"), 405)
        check("duplicate query fields", client.get("/api/v1/products?limit=1&limit=2"), 422)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\0\0" * 16000)
        audio = {"audio": ("sample.wav", buffer.getvalue(), "audio/wav")}
        check(
            "empty speech language",
            client.post("/api/v1/speech/transcriptions", files=audio, data={"language": ""}),
            422,
        )
        meta = client.get("/api/v1/meta").json()
        if meta["speech"]["configuration_state"] == "unconfigured":
            check("valid WAV without Azure key", client.post("/api/v1/speech/transcriptions", files=audio), 503)
        check("health after invalid requests", client.get("/health/ready"), 200)
    report = {
        "passed": all(item["passed"] for item in checks),
        "check_count": len(checks),
        "azure_live_called": False,
        "checks": checks,
    }
    destination = ROOT / "artifacts/backend/runtime-check.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
