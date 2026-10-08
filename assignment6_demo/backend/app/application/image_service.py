import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.domain import AppError


class ImageService:
    @staticmethod
    def decode(raw: bytes, content_type=None):
        if len(raw) > 5_242_880:
            raise AppError(413, "IMAGE_TOO_LARGE", "Ảnh phải nhỏ hơn hoặc bằng 5 MiB.", "image")
        if not raw:
            raise AppError(422, "IMAGE_INVALID", "Ảnh không hợp lệ.", "image")
        formats = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
        declared = (content_type or "application/octet-stream").split(";")[0].strip().lower()
        if declared not in {*formats.values(), "application/octet-stream"}:
            raise AppError(415, "IMAGE_TYPE_UNSUPPORTED", "Chỉ hỗ trợ ảnh JPEG, PNG và WebP.", "image")
        signature = (
            raw.startswith(b"\xff\xd8\xff")
            or raw.startswith(b"\x89PNG\r\n\x1a\n")
            or (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP")
        )
        if not signature:
            raise AppError(415, "IMAGE_TYPE_UNSUPPORTED", "Chỉ hỗ trợ ảnh JPEG, PNG và WebP.", "image")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    fmt = image.format
                    width, height = image.size
                    if fmt not in formats or getattr(image, "n_frames", 1) != 1:
                        raise AppError(
                            415, "IMAGE_TYPE_UNSUPPORTED", "Không hỗ trợ ảnh động hoặc định dạng này.", "image"
                        )
                    if max(width, height) > 8192 or width * height > 16_000_000:
                        raise AppError(413, "IMAGE_DIMENSIONS_EXCEEDED", "Kích thước ảnh vượt giới hạn.", "image")
                    if declared != "application/octet-stream" and declared != formats[fmt]:
                        raise AppError(422, "IMAGE_INVALID", "Định dạng ảnh không khớp nội dung.", "image")
                    image.verify()
                with Image.open(io.BytesIO(raw)) as image:
                    image.load()
                    image = ImageOps.exif_transpose(image)
                    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                        rgba = image.convert("RGBA")
                        decoded = Image.new("RGB", rgba.size, "white")
                        decoded.paste(rgba, mask=rgba.getchannel("A"))
                    else:
                        decoded = image.convert("RGB")
                    return decoded, {"format": fmt, "width": width, "height": height, "byte_size": len(raw)}
        except AppError:
            raise
        except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise AppError(413, "IMAGE_DIMENSIONS_EXCEEDED", "Kích thước ảnh vượt giới hạn.", "image") from exc
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
            raise AppError(422, "IMAGE_INVALID", "Không thể đọc ảnh.", "image") from exc
