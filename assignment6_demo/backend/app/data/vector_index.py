import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np

from app.domain import AppError
from app.data.product_repository import digest, catalog_fingerprint

SCORING_VERSION = "cosine_fusion_v1"


def unit(value):
    vector = np.asarray(value, dtype=np.float32)
    if vector.shape[-1:] != (512,) or vector.ndim not in (1, 2) or not np.isfinite(vector).all():
        raise AppError(500, "INVALID_VECTOR", "Vector tìm kiếm không hợp lệ.")
    norms = np.linalg.norm(vector.astype(np.float64), axis=-1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 1e-12):
        raise AppError(500, "INVALID_VECTOR", "Vector tìm kiếm không hợp lệ.")
    return (vector / norms).astype(np.float32)


class VectorIndex:
    def __init__(self, root, products, model_fingerprint):
        self.available = False
        self.error_code = "INDEX_MISSING"
        self.fingerprint = None
        self.catalog_fingerprint = None
        self.ids = []
        self.product_vectors = np.empty((0, 512), np.float32)
        expected = catalog_fingerprint(products)
        directory = Path(root) / "runtime/index"
        files = sorted(directory.glob("vectors_*.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
        if not files:
            return
        self.error_code = "INDEX_STALE"
        for sidecar in files:
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
                if meta.get("dataset_sha256") != expected or meta.get("model_fingerprint") != model_fingerprint:
                    continue
                self.error_code = "INDEX_CORRUPT"
                fingerprint = meta["fingerprint"]
                payload = dict(meta["fingerprint_payload"])
                if (
                    digest(payload) != fingerprint
                    or sidecar.name != f"vectors_{fingerprint}.json"
                    or payload["dataset_sha256"] != expected
                    or payload["model_fingerprint"] != model_fingerprint
                ):
                    raise ValueError("fingerprint")
                path = directory / f"vectors_{fingerprint}.npz"
                if (
                    path.stat().st_size > 16 * 1024 * 1024
                    or hashlib.sha256(path.read_bytes()).hexdigest() != meta["npz_sha256"]
                ):
                    raise ValueError("checksum")
                with zipfile.ZipFile(path) as archive:
                    infos = archive.infolist()
                    if (
                        len(infos) != 4
                        or {i.filename for i in infos}
                        != {"ids.npy", "text_vectors.npy", "image_vectors.npy", "product_vectors.npy"}
                        or sum(i.file_size for i in infos) > 32 * 1024 * 1024
                    ):
                        raise ValueError("npz entries")
                    for info in infos:
                        with archive.open(info) as member:
                            version = np.lib.format.read_magic(member)
                            if version == (1, 0):
                                shape, _, dtype = np.lib.format.read_array_header_1_0(member, max_header_size=4096)
                            elif version == (2, 0):
                                shape, _, dtype = np.lib.format.read_array_header_2_0(member, max_header_size=4096)
                            else:
                                raise ValueError("npy version")
                            if info.filename == "ids.npy":
                                if shape != (len(products),) or dtype.kind != "U" or dtype.itemsize > 16:
                                    raise ValueError("ids header")
                            elif shape != (len(products), 512) or dtype != np.float32:
                                raise ValueError("vector header")
                            declared_bytes = int(np.prod(shape)) * dtype.itemsize
                            if member.tell() + declared_bytes != info.file_size:
                                raise ValueError("npy size")
                with np.load(path, allow_pickle=False, max_header_size=4096) as data:
                    ids = data["ids"]
                    if (
                        ids.dtype.kind != "U"
                        or ids.ndim != 1
                        or ids.tolist() != sorted(p["product_id"] for p in products)
                    ):
                        self.error_code = "INDEX_OUT_OF_SYNC"
                        raise ValueError("ids")
                    for name in ["text_vectors", "image_vectors", "product_vectors"]:
                        values = data[name]
                        if (
                            values.dtype != np.float32
                            or values.shape != (len(products), 512)
                            or not np.isfinite(values).all()
                            or not np.allclose(np.linalg.norm(values, axis=1), 1, atol=1e-5, rtol=0)
                        ):
                            raise ValueError("vectors")
                    if len(products) and not np.allclose(
                        data["product_vectors"],
                        unit(0.5 * data["text_vectors"] + 0.5 * data["image_vectors"]),
                        atol=1e-5,
                        rtol=0,
                    ):
                        raise ValueError("fusion")
                    self.ids = ids.tolist()
                    self.text_vectors = data["text_vectors"].copy()
                    self.image_vectors = data["image_vectors"].copy()
                    self.product_vectors = data["product_vectors"].copy()
                self.fingerprint = fingerprint
                self.catalog_fingerprint = payload["catalog_fingerprint"]
                self.available = True
                self.error_code = None
                return
            except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
                continue

    def retrieve(self, vector):
        if not self.available:
            raise AppError(503, self.error_code, "Chỉ mục tìm kiếm chưa sẵn sàng.")
        scores = self.product_vectors @ unit(vector)
        if not np.isfinite(scores).all() or np.any(np.abs(scores) > 1 + 1e-5):
            raise AppError(500, "INVALID_VECTOR", "Điểm tìm kiếm không hợp lệ.")
        return [
            {"product_id": pid, "score": float(np.clip(score, -1, 1)), "row": i}
            for i, (pid, score) in enumerate(zip(self.ids, scores))
        ]
