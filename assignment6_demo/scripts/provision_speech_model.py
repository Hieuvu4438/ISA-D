"""Explicit download only; application startup never downloads speech weights."""
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download

MODEL_ID = "Systran/faster-whisper-small"
REVISION = "2ec96c5472da50d38d40c0cfe0602af2e94b4c8a"


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / "models" / "speech-whisper-small"
    snapshot_download(
        MODEL_ID, revision=REVISION, local_dir=target,
        allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "preprocessor_config.json"],
    )
    files = {}
    for item in target.iterdir():
        if item.is_file() and item.name != "manifest.json":
            with item.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            files[item.name] = {"bytes": item.stat().st_size, "sha256": digest}
    manifest = {"model_id": MODEL_ID, "revision": REVISION, "device": "cpu", "compute_type": "int8", "files": files}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model_id": MODEL_ID, "revision": REVISION, "downloaded_bytes": sum(f["bytes"] for f in files.values())}))


if __name__ == "__main__":
    main()
