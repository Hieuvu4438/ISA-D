"""Measure real Groq Whisper-large-v3 Vietnamese STT on frozen FLEURS samples."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.application.speech_service import SpeechService  # noqa: E402
from app.settings import Settings  # noqa: E402


def words(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFC", text).lower()).split()


def distance(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for i, word in enumerate(left, 1):
        next_row = [i]
        for j, candidate in enumerate(right, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j - 1] + (word != candidate)))
        row = next_row
    return row[-1]


async def run(output_path: Path):
    samples = ROOT / "runtime" / "speech-evaluation"
    manifest_path = samples / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Speech manifest not found at {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    settings = Settings.from_env()
    settings.speech_provider = "groq"

    service = SpeechService(settings)
    if not service.available:
        raise RuntimeError("Groq provider unavailable; check GROQ_API_KEY in .env")

    results = []
    try:
        for case in manifest["cases"]:
            audio = (samples / case["audio_path"]).read_bytes()
            if hashlib.sha256(audio).hexdigest() != case["sha256"]:
                raise ValueError("Audio hash mismatch")

            response = await service.transcribe(audio)
            reference, hypothesis = words(case["reference"]), words(response["transcript"])
            case_wer = distance(reference, hypothesis)
            results.append({
                "id": case["id"],
                "audio_path": case["audio_path"],
                "reference": case["reference"],
                "transcript": response["transcript"],
                "word_errors": case_wer,
                "reference_words": len(reference),
                "timing_ms": response["timing_ms"],
                "provider": response["provider"],
            })
            print(
                json.dumps({
                    "id": case["id"],
                    "seconds": round(response["timing_ms"]["total"] / 1000, 2),
                    "transcript": response["transcript"][:60] + "...",
                }, ensure_ascii=False),
                flush=True,
            )
    finally:
        service.close()

    total_ref_words = sum(c["reference_words"] for c in results)
    total_errors = sum(c["word_errors"] for c in results)
    wer = round(total_errors / total_ref_words, 4) if total_ref_words else 0.0

    report = {
        "provider": "groq",
        "model": settings.groq_speech_model,
        "api_endpoint": "https://api.groq.com/openai/v1/audio/transcriptions",
        "cases": results,
        "sample_count": len(results),
        "total_reference_words": total_ref_words,
        "total_word_errors": total_errors,
        "wer": wer,
        "azure_recognition_calls": 0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {output_path} (WER: {wer * 100:.2f}%)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "backend" / "speech-groq-check.json"))
    args = parser.parse_args()
    asyncio.run(run(Path(args.output)))


if __name__ == "__main__":
    main()
