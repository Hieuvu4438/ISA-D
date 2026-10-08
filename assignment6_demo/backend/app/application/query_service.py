from dataclasses import dataclass
from time import perf_counter

import numpy as np

from app.domain import AppError, SearchOptions, normalize_text
from app.data.vector_index import unit
from app.application.image_service import ImageService


@dataclass
class Query:
    mode: str
    vector: np.ndarray
    text_vector: np.ndarray | None
    image_vector: np.ndarray | None
    options: SearchOptions
    input_summary: dict
    text_weight: float | None = None
    voice_source: str | None = None
    validation_ms: float = 0
    encoding_ms: float = 0
    started_at: float = 0


class QueryService:
    def __init__(self, encoder):
        self.encoder = encoder

    def _text(self, text):
        if not isinstance(text, str) or not normalize_text(text) or len(normalize_text(text)) > 500:
            raise AppError(422, "VALIDATION_ERROR", "Mô tả phải có từ 1 đến 500 ký tự.", "text")
        return self.encoder.validate_text(normalize_text(text))

    def build_text(self, mode, text, options, voice_source=None):
        start = perf_counter()
        if (
            mode not in ("text", "voice")
            or (mode == "voice" and voice_source not in ("azure", "local", "manual_transcript"))
            or (mode == "text" and voice_source is not None)
        ):
            raise AppError(422, "VALIDATION_ERROR", "Nguồn truy vấn không hợp lệ.")
        text = self._text(text)
        validation = (perf_counter() - start) * 1000
        encoded = perf_counter()
        vector = unit(self.encoder.encode_texts([text])[0])
        return Query(
            mode,
            vector,
            vector,
            None,
            options,
            {"text": text, "image_summary": None},
            voice_source=voice_source,
            validation_ms=validation,
            encoding_ms=(perf_counter() - encoded) * 1000,
            started_at=start,
        )

    def build_image(self, image_bytes, options, content_type=None):
        start = perf_counter()
        image, summary = ImageService.decode(image_bytes, content_type)
        validation = (perf_counter() - start) * 1000
        encoded = perf_counter()
        vector = unit(self.encoder.encode_images([image])[0])
        return Query(
            "image",
            vector,
            None,
            vector,
            options,
            {"text": None, "image_summary": summary},
            validation_ms=validation,
            encoding_ms=(perf_counter() - encoded) * 1000,
            started_at=start,
        )

    def build_multimodal(self, text, image_bytes, options, text_weight=0.5, content_type=None):
        start = perf_counter()
        if type(text_weight) not in (int, float) or not np.isfinite(text_weight) or not 0.1 <= text_weight <= 0.9:
            raise AppError(422, "VALIDATION_ERROR", "Trọng số text phải từ 0.1 đến 0.9.", "text_weight")
        text = self._text(text)
        image, summary = ImageService.decode(image_bytes, content_type)
        validation = (perf_counter() - start) * 1000
        encoded = perf_counter()
        qt = unit(self.encoder.encode_texts([text])[0])
        qi = unit(self.encoder.encode_images([image])[0])
        vector = unit(text_weight * qt + (1 - text_weight) * qi)
        return Query(
            "multimodal",
            vector,
            qt,
            qi,
            options,
            {"text": text, "image_summary": summary},
            text_weight=text_weight,
            validation_ms=validation,
            encoding_ms=(perf_counter() - encoded) * 1000,
            started_at=start,
        )
