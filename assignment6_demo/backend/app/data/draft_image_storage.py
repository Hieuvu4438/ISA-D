"""Content-addressed uploaded bytes; no remote URL fetch or public mount."""
import hashlib
import os
from pathlib import Path
from uuid import uuid4

from app.domain import AppError


class DraftImageStorage:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.directory = self.root / "runtime/catalog/assets"

    def store(self, raw, image_format):
        sha = hashlib.sha256(raw).hexdigest()
        suffix = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
        if not self.directory.resolve().is_relative_to(self.root):
            raise AppError(503, "DRAFT_IMAGE_UNAVAILABLE", "Kho ảnh bản nháp chưa sẵn sàng.")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{sha}.{suffix}"
        if path.exists():
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise AppError(503, "DRAFT_IMAGE_UNAVAILABLE", "Ảnh bản nháp không khớp checksum.")
        else:
            temp = self.directory / f".{uuid4().hex}.tmp"
            try:
                temp.write_bytes(raw)
                os.replace(temp, path)
            finally:
                temp.unlink(missing_ok=True)
        return path.relative_to(self.root).as_posix(), sha

    def read(self, asset):
        try:
            path = (self.root / asset["local_path"]).resolve()
            allowed = ((self.root / "data/images").resolve(), self.directory.resolve())
            if not path.is_relative_to(self.root) or not any(path.is_relative_to(directory) for directory in allowed) or not path.is_file():
                raise ValueError("unsafe path")
            raw = path.read_bytes()
            if len(raw) > 5_242_880 or hashlib.sha256(raw).hexdigest() != asset["sha256"] or len(raw) != asset["bytes"]:
                raise ValueError("checksum")
            return path, raw
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise AppError(503, "DRAFT_IMAGE_UNAVAILABLE", "Ảnh bản nháp thiếu hoặc đã thay đổi. Hãy tải lại ảnh.") from exc
