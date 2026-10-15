"""Strict authoring DTOs; draft metadata never changes the live catalog implicitly."""
from datetime import date
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, StrictInt, field_validator

from app.domain import CategoryCode, StrictModel, normalize_text

METADATA_FIELDS = ("name", "brand", "category", "color", "price_vnd", "description")


class DraftMetadata(StrictModel):
    name: str = Field(strict=True, min_length=1, max_length=120)
    brand: str = Field(strict=True, min_length=1, max_length=120)
    category: CategoryCode
    color: str = Field(strict=True, min_length=1, max_length=120)
    price_vnd: StrictInt = Field(ge=0, le=1_000_000_000)
    description: str = Field(strict=True, min_length=1, max_length=500)

    @field_validator("name", "brand", "color", "description")
    @classmethod
    def text(cls, value):
        if any(ord(c) < 32 for c in value):
            raise ValueError("Không dùng ký tự điều khiển")
        value = normalize_text(value)
        if not value:
            raise ValueError("Nội dung không được rỗng")
        return value


class DraftVersion(StrictModel):
    version: StrictInt = Field(ge=0, le=1_000_000_000)


class DraftSave(DraftVersion):
    base_catalog_fingerprint: str = Field(strict=True, pattern=r"^[a-f0-9]{64}$")
    product: DraftMetadata


class PhotoProvenance(StrictModel):
    source_page: str = Field(strict=True, max_length=2000)
    original_url: str = Field(strict=True, max_length=2000)
    download_url: str = Field(strict=True, max_length=2000)
    transformations: str = Field(strict=True, min_length=1, max_length=500)
    author: str = Field(strict=True, min_length=1, max_length=200)
    license: str = Field(strict=True, min_length=1, max_length=120)
    license_url: str = Field(strict=True, max_length=2000)
    retrieved_at: date
    real_photo_review: Literal["passed"]

    @field_validator("retrieved_at", mode="before")
    @classmethod
    def date_string(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) or date.fromisoformat(value) > date.today():
            raise ValueError("Ngày lấy ảnh cần YYYY-MM-DD, không ở tương lai")
        return value

    @field_validator("source_page", "original_url", "download_url", "license_url")
    @classmethod
    def https_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError("Nguồn ảnh cần URL HTTPS không chứa thông tin đăng nhập")
        return value

    @field_validator("author", "license", "transformations")
    @classmethod
    def credit(cls, value):
        return DraftMetadata.text(value)
