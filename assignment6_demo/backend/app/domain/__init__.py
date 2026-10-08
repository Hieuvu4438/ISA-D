from typing import Literal
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator, field_validator


class AppError(Exception):
    def __init__(self, status, code, message, field=None, retryable=False):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        self.retryable = retryable


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


CategoryCode = Literal[
    "running_shoes", "trail_shoes", "casual_shoes", "boots", "sandals", "bag",
    "backpack", "tote_bag", "t_shirt", "jacket", "watch", "sunglasses",
]


class Filters(StrictModel):
    category: CategoryCode | None = None
    brand: str | None = None
    min_price: StrictInt | None = Field(default=None, ge=0, le=1_000_000_000)
    max_price: StrictInt | None = Field(default=None, ge=0, le=1_000_000_000)
    in_stock: StrictBool = False

    @field_validator("brand")
    @classmethod
    def brand_valid(cls, value):
        if value is None:
            return value
        value = normalize_text(value)
        if not value:
            raise ValueError("Thương hiệu không được rỗng.")
        return value

    @model_validator(mode="after")
    def bounds(self):
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("Giá tối thiểu phải nhỏ hơn hoặc bằng giá tối đa.")
        return self


class SearchOptions(StrictModel):
    top_k: StrictInt = Field(default=5, ge=1, le=20)
    result_policy: Literal["nearest", "relevant"] = "nearest"
    filters: Filters = Field(default_factory=Filters)


class TextRequest(StrictModel):
    mode: Literal["text", "voice"]
    text: str = Field(strict=True)
    voice_source: Literal["azure", "local", "manual_transcript"] | None = None
    options: SearchOptions = Field(default_factory=SearchOptions)

    @field_validator("text")
    @classmethod
    def text_valid(cls, value):
        value = normalize_text(value)
        if not value or len(value) > 500:
            raise ValueError("Mô tả phải có từ 1 đến 500 ký tự.")
        return value

    @model_validator(mode="after")
    def voice_valid(self):
        if self.mode == "voice" and self.voice_source is None:
            raise ValueError("Voice cần nguồn transcript.")
        if self.mode == "text" and "voice_source" in self.model_fields_set:
            raise ValueError("Text không nhận voice_source.")
        return self
