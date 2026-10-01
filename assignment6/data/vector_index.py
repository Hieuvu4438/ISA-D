"""Unsorted cosine candidate scoring and source fingerprints."""

import hashlib
import json
from pathlib import Path

import numpy as np


def cosine_similarity(a, b):
    try:
        left, right = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("vectors must be numeric") from exc
    if left.ndim != 1 or left.shape != right.shape or not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("vectors require matching dimensions and finite values")
    denominator = np.linalg.norm(left) * np.linalg.norm(right)
    return float(np.clip(np.dot(left, right) / denominator, -1, 1)) if denominator else 0.0


def source_fingerprint(products, root):
    digest = hashlib.sha256(json.dumps(products, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for p in products:
        digest.update((Path(root) / p["image"]).read_bytes())
    return digest.hexdigest()


class VectorIndex:
    def __init__(self, path=None, products=None, root=None):
        self.path = Path(path or Path(__file__).with_name("embeddings.json"))
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.encoder = payload["encoder"]
            self.dimension = self.encoder["dimension"]
            self.vectors = {int(k): np.asarray(v, dtype=float).tolist() for k, v in payload["vectors"].items()}
            if self.encoder != {"name": "rgbhist-gray-thumbnail", "version": "1.0", "dimension": 88}:
                raise ValueError("unsupported encoder metadata")
            if any(np.asarray(v).shape != (self.dimension,) or not np.isfinite(v).all() for v in self.vectors.values()):
                raise ValueError("invalid stored embedding")
            if products is not None:
                if set(self.vectors) != {p["product_id"] for p in products}:
                    raise ValueError("index product IDs do not match catalogue")
                if payload["source_sha256"] != source_fingerprint(products, root):
                    raise ValueError("stale image index; run scripts/build_index.py")
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid image index; run scripts/build_index.py") from exc

    def score(self, embedding):
        if np.asarray(embedding).shape != (self.dimension,):
            raise ValueError("query vector dimension does not match index")
        return {
            identifier: max(0.0, cosine_similarity(embedding, vector)) for identifier, vector in self.vectors.items()
        }
