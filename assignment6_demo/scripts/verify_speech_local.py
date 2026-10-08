"""Measure real local Vietnamese STT on frozen FLEURS samples, without Azure."""
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


def words(text):
    return re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFC", text).lower()).split()


def distance(left, right):
    row = list(range(len(right) + 1))
    for i, word in enumerate(left, 1):
        next_row = [i]
        for j, candidate in enumerate(right, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j-1] + (word != candidate)))
        row = next_row
    return row[-1]


async def run(model_path, output):
    samples = ROOT / "runtime" / "speech-evaluation"
    manifest = json.loads((samples / "manifest.json").read_text(encoding="utf-8"))
    started = time.perf_counter()
    service = SpeechService(Settings(root=ROOT, speech_provider="local", local_speech_model_path=model_path))
    load_seconds = time.perf_counter() - started
    if not service.available:
        raise RuntimeError("Local model unavailable; provision it first")
    results = []
    try:
        for case in manifest["cases"]:
            audio = (samples / case["audio_path"]).read_bytes()
            if hashlib.sha256(audio).hexdigest() != case["sha256"]:
                raise ValueError("Audio hash mismatch")
            response = await service.transcribe(audio)
            reference, hypothesis = words(case["reference"]), words(response["transcript"])
            results.append({**case, "transcript": response["transcript"], "word_errors": distance(reference, hypothesis),
                            "reference_words": len(reference), "timing_ms": response["timing_ms"],
                            "provider": response["provider"]})
            print(json.dumps({"id": case["id"], "seconds": response["timing_ms"]["total"] / 1000}, ensure_ascii=True), flush=True)
    finally:
        service.close()
    report = {"provider": "local", "device": "cpu", "compute_type": "int8", "cpu_threads": 4,
              "model": json.loads((model_path / "manifest.json").read_text(encoding="utf-8")),
              "dataset": {key: value for key, value in manifest.items() if key != "cases"},
              "load_seconds": round(load_seconds, 3), "cases": results,
              "wer": sum(c["word_errors"] for c in results) / sum(c["reference_words"] for c in results),
              "azure_recognition_calls": 0,
              "limitations": "Five fixed public samples; not user microphone, accents, noisy audio or product names acceptance."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(results), "wer": report["wer"], "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, default=ROOT / "models" / "speech-whisper-small")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "backend" / "speech-local-check.json")
    args = parser.parse_args()
    asyncio.run(run(args.model_path, args.output))
