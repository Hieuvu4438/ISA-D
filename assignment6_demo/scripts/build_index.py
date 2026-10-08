"""Build the real 512D fused catalog vectors from local CPU model files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    from app.application.embedding_service import AIEmbeddingService
    from app.application.index_builder import build_index
    from app.data.product_repository import ProductRepository

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    repository = ProductRepository(root)
    encoder = AIEmbeddingService(root)
    if not encoder.available:
        raise SystemExit("Model chưa sẵn sàng: chạy scripts/download_models.py trước.")
    metadata = build_index(root, repository, encoder)
    target = root / "artifacts/backend/index-build.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
