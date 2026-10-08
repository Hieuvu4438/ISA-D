import importlib.metadata
import json
import os
from pathlib import Path

import numpy as np

from app.domain import AppError, normalize_text
from app.settings import TEXT_MODEL_ID, IMAGE_MODEL_ID, TEXT_REVISION, IMAGE_REVISION
from app.data.product_repository import digest
from app.data.vector_index import unit


class AIEmbeddingService:
    def __init__(self, root: Path):
        self.available = False
        self.error_code = "MODEL_UNAVAILABLE"
        self.model_fingerprint = None
        root = Path(root)
        try:
            manifest = json.loads((root / "runtime/models/model_manifest.json").read_text(encoding="utf-8"))
            expected = {
                "text_model_id": TEXT_MODEL_ID,
                "image_model_id": IMAGE_MODEL_ID,
                "text_revision": TEXT_REVISION,
                "image_revision": IMAGE_REVISION,
            }
            if any(manifest.get(k) != v for k, v in expected.items()):
                return
            versions = {
                p: importlib.metadata.version(p)
                for p in ["sentence-transformers", "transformers", "torch", "numpy", "Pillow"]
            }
            recorded = manifest.get("package_versions", {})
            if recorded and any(recorded.get(k) != v for k, v in versions.items()):
                return
            text_dir, image_dir = root / "runtime/models/text", root / "runtime/models/image"
            if not text_dir.is_dir() or not image_dir.is_dir():
                return
            import torch
            from sentence_transformers import SentenceTransformer

            torch.set_num_threads(min(4, os.cpu_count() or 1))
            self.text_model = SentenceTransformer(
                str(text_dir), device="cpu", local_files_only=True, trust_remote_code=False
            )
            self.image_model = SentenceTransformer(
                str(image_dir), device="cpu", local_files_only=True, trust_remote_code=False
            )
            self.text_model.eval()
            self.image_model.eval()
            self.tokenizer = self.text_model[0].tokenizer
            self.model_fingerprint = digest(
                {
                    **expected,
                    "package_versions": versions,
                    "dimension": 512,
                    "preprocess_version": "image_rgb_exif_white_v1",
                }
            )
            self.available = True
            self.error_code = None
        except Exception:
            self.available = False
            self.error_code = "MODEL_UNAVAILABLE"

    def validate_text(self, text):
        if not isinstance(text, str):
            raise AppError(422, "VALIDATION_ERROR", "Mô tả phải là chuỗi.", "text")
        text = normalize_text(text)
        if not text:
            raise AppError(422, "VALIDATION_ERROR", "Vui lòng nhập mô tả.", "text")
        if len(text) > 500:
            raise AppError(422, "TEXT_TOO_LONG", "Mô tả phải có tối đa 500 ký tự.", "text")
        if not self.available:
            raise AppError(503, "MODEL_UNAVAILABLE", "Model tìm kiếm chưa sẵn sàng.")
        ids = self.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]
        if len(ids) > 128:
            raise AppError(422, "TEXT_TOO_LONG", "Mô tả vượt giới hạn 128 tokens.", "text")
        return text

    def _encode(self, model, values):
        if not self.available:
            raise AppError(503, "MODEL_UNAVAILABLE", "Model tìm kiếm chưa sẵn sàng.")
        if not values:
            return np.empty((0, 512), np.float32)
        import torch

        with torch.inference_mode():
            encoded = model.encode(
                values, batch_size=8, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
            )
        return unit(encoded)

    def encode_texts(self, texts):
        if not self.available:
            raise AppError(503, "MODEL_UNAVAILABLE", "Model tìm kiếm chưa sẵn sàng.")
        return self._encode(self.text_model, [self.validate_text(t) for t in texts])

    def encode_images(self, images):
        if not self.available:
            raise AppError(503, "MODEL_UNAVAILABLE", "Model tìm kiếm chưa sẵn sàng.")
        return self._encode(self.image_model, images)
