"""Download the pinned CPU encoders once; inference remains offline."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

MODELS = {
    "text": ("sentence-transformers/clip-ViT-B-32-multilingual-v1", "58edf8cada9e398793dca955574a48cbb7f18be2"),
    "image": ("sentence-transformers/clip-ViT-B-32", "327ab6726d33c0e22f920c83f2ff9e4bd38ca37f"),
}
ROOT = Path(__file__).resolve().parents[1]


def download(kind: str, destination: Path) -> None:
    from huggingface_hub import HfApi, snapshot_download

    model_id, revision = MODELS[kind]
    names = HfApi().list_repo_files(model_id, revision=revision)
    # One framework and one weight format per directory avoids several GB of extras.
    safe_dirs = {str(Path(name).parent) for name in names if name.endswith(".safetensors")}
    selected = []
    for name in names:
        if any(part in {"onnx", "openvino", "tf", "flax"} for part in Path(name).parts):
            continue
        if name.endswith((".json", ".txt", ".model", ".safetensors")):
            selected.append(name)
        elif name.endswith("pytorch_model.bin") and str(Path(name).parent) not in safe_dirs:
            selected.append(name)
    print(f"Downloading {kind}: {model_id}@{revision} ({len(selected)} files)", flush=True)
    snapshot_download(
        repo_id=model_id, revision=revision, local_dir=str(destination / kind), allow_patterns=selected, max_workers=3
    )
    print(f"Ready: {kind}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    destination = args.root.resolve() / "runtime" / "models"
    destination.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(download, kind, destination) for kind in MODELS]
        for future in futures:
            future.result()
    packages = {}
    for package in ("sentence-transformers", "transformers", "torch", "numpy", "Pillow", "huggingface-hub"):
        packages[package] = importlib.metadata.version(package)
    manifest = {
        "schema_version": 1,
        "text_model_id": MODELS["text"][0],
        "text_revision": MODELS["text"][1],
        "image_model_id": MODELS["image"][0],
        "image_revision": MODELS["image"][1],
        "package_versions": packages,
        "downloaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    path = destination / "model_manifest.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    print(f"Manifest: {path}")


if __name__ == "__main__":
    main()
