"""Offline application orchestration; Data only validates and retrieves stored vectors."""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from app.domain import AppError
from app.data.product_repository import digest, catalog_fingerprint, product_text
from app.data.vector_index import SCORING_VERSION, VectorIndex, unit


def build_index(root, repository, encoder):
    if not encoder.available:
        raise AppError(503, "MODEL_UNAVAILABLE", "Model tìm kiếm chưa sẵn sàng.")
    products = repository.products
    texts = [product_text(p) for p in products]
    for text in texts:
        encoder.validate_text(text)
    images = []
    for product in products:
        path, _, _ = repository.image_file(product["product_id"])
        with Image.open(path) as image:
            images.append(ImageOps.exif_transpose(image).convert("RGB").copy())
    text_vectors = unit(encoder.encode_texts(texts)) if products else np.empty((0, 512), np.float32)
    image_vectors = unit(encoder.encode_images(images)) if products else np.empty((0, 512), np.float32)
    vectors = unit(0.5 * text_vectors + 0.5 * image_vectors) if products else np.empty((0, 512), np.float32)
    payload = {
        "schema_version": 1,
        "dataset_sha256": catalog_fingerprint(products),
        "catalog_fingerprint": repository.fingerprint,
        "image_sha256_by_id": repository.image_hashes,
        "model_fingerprint": encoder.model_fingerprint,
        "dimension": 512,
        "dtype": "float32",
        "product_text_weight": 0.5,
        "preprocess_version": "image_rgb_exif_white_v1",
        "text_template_version": "product_text_v1_vi",
        "scoring_version": SCORING_VERSION,
    }
    fingerprint = digest(payload)
    directory = Path(root) / "runtime/index"
    directory.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    temp = directory / f".{token}.npz"
    temp_meta = directory / f".{token}.json"
    try:
        np.savez_compressed(
            temp,
            ids=np.array([p["product_id"] for p in products], dtype="U4"),
            text_vectors=text_vectors,
            image_vectors=image_vectors,
            product_vectors=vectors,
        )
        meta = {
            **payload,
            "fingerprint": fingerprint,
            "fingerprint_payload": payload,
            "sorted_ids": [p["product_id"] for p in products],
            "npz_sha256": hashlib.sha256(temp.read_bytes()).hexdigest(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        temp_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, directory / f"vectors_{fingerprint}.npz")
        os.replace(temp_meta, directory / f"vectors_{fingerprint}.json")
        loaded = VectorIndex(root, products, encoder.model_fingerprint)
        if not loaded.available:
            raise ValueError("published index invalid")
        return meta
    finally:
        temp.unlink(missing_ok=True)
        temp_meta.unlink(missing_ok=True)
