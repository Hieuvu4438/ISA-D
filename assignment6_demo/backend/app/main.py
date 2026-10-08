import json
import math
import re
from contextlib import asynccontextmanager
from types import SimpleNamespace
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import ValidationError
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

from app.application.embedding_service import AIEmbeddingService
from app.application.query_service import QueryService
from app.application.search_service import SearchService
from app.application.speech_service import SpeechService
from app.data.order_repository import OrderRepository
from app.data.product_repository import CATEGORIES, ProductRepository
from app.data.vector_index import VectorIndex
from app.domain import AppError, SearchOptions, TextRequest
from app.runner import AsyncBoundedRunner
from app.settings import Settings, TEXT_MODEL_ID, IMAGE_MODEL_ID, TEXT_REVISION, IMAGE_REVISION


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def invalid(_):
        raise ValueError("non-finite number")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite number")
        return number

    try:
        decoded = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite_float)
        pending = [decoded]
        while pending:
            value = pending.pop()
            if isinstance(value, str):
                value.encode("utf-8")
            elif isinstance(value, dict):
                pending.extend(value.keys())
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        return decoded
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AppError(400, "INVALID_JSON", "JSON không hợp lệ, chứa khóa trùng hoặc giá trị không hỗ trợ.") from exc


class Container:
    def __init__(self, settings):
        self.settings = settings
        self.errors = {}
        self.products = self.orders = None
        for name, factory in [("products", ProductRepository), ("orders", OrderRepository)]:
            try:
                setattr(self, name, factory(settings.root))
            except AppError as exc:
                self.errors[name] = exc
        self.encoder = (
            AIEmbeddingService(settings.root)
            if settings.load_models
            else SimpleNamespace(available=False, error_code="MODEL_UNAVAILABLE", model_fingerprint=None)
        )
        self.index = VectorIndex(
            settings.root, self.products.products if self.products else [], self.encoder.model_fingerprint
        )
        self.search = SearchService(self.products, self.encoder, self.index, settings.root)
        self.queries = QueryService(self.encoder)
        self.speech = SpeechService(settings)
        self.runner = AsyncBoundedRunner()

    def require(self, name):
        if name in self.errors:
            raise self.errors[name]
        return getattr(self, name)

    def close(self):
        self.runner.close()
        self.speech.close()


def error_response(request, error):
    body = {
        "code": error.code,
        "message": error.message,
        "request_id": request.state.request_id,
        "retryable": error.retryable,
        "field_errors": [{"field": error.field, "message": error.message}] if error.field else [],
    }
    headers = {"Retry-After": "2" if error.code == "SEARCH_BUSY" else "5"} if error.status == 429 else {}
    return JSONResponse({"error": body}, status_code=error.status, headers=headers)


def query_fields(request, allowed=()):
    names = [name for name, _ in request.query_params.multi_items()]
    if len(names) != len(set(names)) or any(name not in allowed for name in names):
        raise AppError(422, "VALIDATION_ERROR", "Tham số truy vấn không hợp lệ.")


def identifier(value, prefix):
    if not re.fullmatch(prefix + r"[0-9]{3}", value):
        raise AppError(422, "VALIDATION_ERROR", "Mã không đúng định dạng.")
    return value


async def multipart(request, names, upload_name):
    query_fields(request)
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi multipart/form-data.")
    async with request.form(max_files=1, max_fields=5, max_part_size=5 * 1024 * 1024) as form:
        fields = [name for name, _ in form.multi_items()]
        if len(fields) != len(set(fields)) or any(name not in names for name in fields):
            raise AppError(422, "VALIDATION_ERROR", "Trường multipart không hợp lệ.")
        upload = form.get(upload_name)
        if not isinstance(upload, UploadFile):
            raise AppError(422, "VALIDATION_ERROR", "Thiếu tệp tải lên.", upload_name)
        values = {}
        text_size = 0
        for name in names:
            if name == upload_name:
                continue
            value = form.get(name)
            if value is not None and not isinstance(value, str):
                raise AppError(422, "VALIDATION_ERROR", "Trường văn bản không hợp lệ.", name)
            values[name] = value
            text_size += len(value.encode("utf-8")) if value is not None else 0
        if text_size > 16 * 1024:
            raise AppError(413, "REQUEST_TOO_LARGE", "Các trường văn bản quá lớn.")
        raw = await upload.read(5 * 1024 * 1024 + 1)
        return values, raw, upload.content_type


def options_value(value):
    try:
        return SearchOptions.model_validate(strict_json(value) if value is not None else {})
    except ValidationError as exc:
        raise AppError(422, "VALIDATION_ERROR", "Tùy chọn tìm kiếm không hợp lệ.", "options") from exc


def form_schema(file_name, text_fields):
    properties = {file_name: {"type": "string", "format": "binary"}}
    properties.update({name: {"type": "string"} for name in text_fields})
    return {
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {"schema": {"type": "object", "required": [file_name], "properties": properties}}
            },
        }
    }


def create_app(settings=None, container=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application):
        application.state.services = container or Container(settings)
        yield
        application.state.services.close()

    application = FastAPI(
        title="ISA-D Demo Backend",
        version="0.1.0",
        lifespan=lifespan,
        description="Tìm sản phẩm bằng tiếng Việt, ảnh, text + ảnh; Azure Speech và tra đơn hàng demo.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def request_boundary(request, call_next):
        request.state.request_id = str(uuid4())
        try:
            if (
                any(
                    name in request.headers
                    for name in ("customer_id", "customer-id", "x-customer-id", "x-demo-customer-id")
                )
                or "customer_id" in request.query_params
            ):
                raise AppError(422, "CLIENT_CUSTOMER_CONTEXT_FORBIDDEN", "Khách hàng demo được xác định tại backend.")
            if request.method == "POST":
                limit = 2 * 1024 * 1024 if "/speech/" in request.url.path else 6 * 1024 * 1024
                if request.headers.get("content-type", "").lower().startswith("application/json"):
                    limit = 16 * 1024
                chunks, size = [], 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > limit:
                        raise AppError(413, "REQUEST_TOO_LARGE", "Dữ liệu tải lên quá lớn.")
                    chunks.append(chunk)
                request._body = b"".join(chunks)
                if request.headers.get("content-type", "").lower().startswith("application/json"):
                    strict_json(request._body)
                elif request.url.path == "/api/v1/search":
                    raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")
            response = await call_next(request)
        except AppError as exc:
            response = error_response(request, exc)
        except Exception:
            response = error_response(request, AppError(500, "INTERNAL_ERROR", "Không thể xử lý yêu cầu."))
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.exception_handler(AppError)
    async def app_error(request, exc):
        return error_response(request, exc)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        location = exc.errors()[0].get("loc", ()) if exc.errors() else ()
        field = ".".join(str(part) for part in location if part != "body") or None
        return error_response(request, AppError(422, "VALIDATION_ERROR", "Dữ liệu đầu vào không hợp lệ.", field))

    @application.exception_handler(HTTPException)
    async def http_error(request, exc):
        response = error_response(
            request,
            AppError(
                exc.status_code,
                {404: "ROUTE_NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR"),
                "Không tìm thấy đường dẫn." if exc.status_code == 404 else "Yêu cầu không hợp lệ.",
            ),
        )
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    def services(request):
        return request.app.state.services

    async def search_result(request, build):
        started = perf_counter()
        svc = services(request)
        svc.require("products")
        if not svc.search.available:
            raise AppError(503, svc.search.reason_code, "Tìm kiếm chưa sẵn sàng.")
        result = await svc.runner.run(lambda: svc.search.search(build(svc.queries)), settings.search_timeout)
        result["meta"]["timing_ms"]["total"] = (perf_counter() - started) * 1000
        return {"request_id": request.state.request_id, **result}

    @application.get("/health/live")
    async def live(request: Request):
        query_fields(request)
        return {"request_id": request.state.request_id, "status": "live"}

    @application.get("/health/ready")
    async def ready(request: Request):
        query_fields(request)
        svc = services(request)
        reasons = []
        if svc.products is None:
            reasons.append("CATALOG_UNAVAILABLE")
        if not svc.encoder.available:
            reasons.append("MODEL_UNAVAILABLE")
        if not svc.index.available:
            reasons.append(svc.index.error_code)
        ok = not reasons
        return JSONResponse(
            {
                "request_id": request.state.request_id,
                "status": "ready" if ok else "not_ready",
                "search_available": ok,
                "reason_codes": reasons,
            },
            status_code=200 if ok else 503,
        )

    @application.get("/api/v1/meta")
    async def meta(request: Request):
        query_fields(request)
        svc = services(request)
        products = svc.products.products if svc.products is not None else []
        policies = svc.search.policies if svc.search.available else []
        modes = sorted(
            {p["mode"] for p in policies} | ({"voice"} if any(p["mode"] == "text" for p in policies) else set())
        )

        def capability(available, code):
            return {"available": available, "reason_code": None if available else code}

        return {
            "request_id": request.state.request_id,
            "api_version": "v1",
            "capabilities": {
                "catalog": capability(svc.products is not None, "CATALOG_UNAVAILABLE"),
                "orders": capability(svc.orders is not None, "ORDERS_UNAVAILABLE"),
                "search": capability(
                    svc.products is not None and svc.search.available,
                    "CATALOG_UNAVAILABLE" if svc.products is None else svc.search.reason_code,
                ),
                "manual_transcript": capability(True, None),
                "relevant": {
                    **capability(bool(policies), "RELEVANCE_POLICY_UNAVAILABLE"),
                    "modes": modes,
                    "multimodal_weights": sorted({p["text_weight"] for p in policies if p["mode"] == "multimodal"}),
                },
            },
            "model": {
                "text_model_id": TEXT_MODEL_ID,
                "image_model_id": IMAGE_MODEL_ID,
                "text_revision": TEXT_REVISION if svc.encoder.available else None,
                "image_revision": IMAGE_REVISION if svc.encoder.available else None,
                "dimension": 512,
                "model_fingerprint": svc.encoder.model_fingerprint,
            },
            "index": {
                "available": svc.index.available,
                "index_fingerprint": svc.index.fingerprint,
                "catalog_fingerprint": svc.products.fingerprint if svc.products else None,
                "product_count": len(products),
            },
            "filters": {
                "available": svc.products is not None,
                "categories": sorted(CATEGORIES),
                "brands": sorted({p["brand"] for p in products}),
                "min_price": min((p["price_vnd"] for p in products), default=None),
                "max_price": max((p["price_vnd"] for p in products), default=None),
            },
            "limits": {
                "text_max_characters": 500,
                "text_max_tokens": 128,
                "top_k_max": 20,
                "image_max_bytes": 5 * 1024 * 1024,
                "image_max_pixels": 16_000_000,
                "image_max_dimension": 8192,
                "text_weight_min": 0.1,
                "text_weight_max": 0.9,
            },
            "speech": {
                "provider": "azure",
                "configuration_state": svc.speech.configuration_state,
                "region": settings.speech_region if settings.speech_region == "southeastasia" else None,
                "language": "vi-VN",
                "accepted_formats": ["wav_pcm16_mono_16000"],
                "max_duration_seconds": 15,
                "max_bytes": 1048576,
            },
        }

    @application.get("/api/v1/products")
    async def products(request: Request):
        query_fields(request, ("offset", "limit"))
        values = {}
        for name, default, maximum in [("offset", 0, 1_000_000), ("limit", 12, 100)]:
            raw = request.query_params.get(name, str(default))
            if not re.fullmatch(r"[0-9]{1,7}", raw) or not (0 if name == "offset" else 1) <= int(raw) <= maximum:
                raise AppError(422, "VALIDATION_ERROR", "Phân trang không hợp lệ.", name)
            values[name] = int(raw)
        repo = services(request).require("products")
        rows = repo.products
        return {
            "request_id": request.state.request_id,
            "products": [repo.summary(p) for p in rows[values["offset"] : values["offset"] + values["limit"]]],
            "total": len(rows),
            **values,
        }

    @application.get("/api/v1/products/{product_id}")
    async def product_detail(product_id: str, request: Request):
        query_fields(request)
        repo = services(request).require("products")
        product = repo.get_by_id(identifier(product_id, "P"))
        if product is None:
            raise AppError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
        return {"request_id": request.state.request_id, "product": repo.detail(product)}

    @application.get("/api/v1/credits")
    async def credits(request: Request):
        query_fields(request)
        return {"request_id": request.state.request_id, "credits": services(request).require("products").credits()}

    @application.get("/api/v1/media/products/{product_id}")
    async def media(product_id: str, request: Request):
        query_fields(request)
        path, mime, checksum = services(request).require("products").image_file(identifier(product_id, "P"))
        etag = f'"{checksum}"'
        if etag in [value.strip() for value in request.headers.get("if-none-match", "").split(",")]:
            return Response(status_code=304, headers={"ETag": etag})
        return FileResponse(path, media_type=mime, headers={"ETag": etag})

    def order_value(request, order_id):
        order = services(request).require("orders").find_order(settings.customer_id, identifier(order_id, "O"))
        if order is None:
            raise AppError(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
        return {"request_id": request.state.request_id, "order": {k: v for k, v in order.items() if k != "customer_id"}}

    @application.get("/api/v1/orders")
    async def order_query(request: Request):
        query_fields(request, ("order_id",))
        result = order_value(request, request.query_params.get("order_id", "").strip().upper())
        result["order"].pop("items")
        return result

    @application.get("/api/v1/orders/{order_id}")
    async def order_path(order_id: str, request: Request):
        query_fields(request)
        return order_value(request, order_id)

    @application.post("/api/v1/search")
    async def text_search(body: TextRequest, request: Request):
        query_fields(request)
        if not request.headers.get("content-type", "").lower().startswith("application/json"):
            raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")
        return await search_result(
            request, lambda queries: queries.build_text(body.mode, body.text, body.options, body.voice_source)
        )

    @application.post("/api/v1/search/image", openapi_extra=form_schema("image", ["options"]))
    async def image_search(request: Request):
        fields, blob, mime = await multipart(request, ("image", "options"), "image")
        options = options_value(fields["options"])
        return await search_result(request, lambda queries: queries.build_image(blob, options, mime))

    @application.post(
        "/api/v1/search/multimodal", openapi_extra=form_schema("image", ["text", "text_weight", "options"])
    )
    async def multimodal_search(request: Request):
        fields, blob, mime = await multipart(request, ("image", "text", "text_weight", "options"), "image")
        options = options_value(fields["options"])
        try:
            weight = strict_json(fields["text_weight"]) if fields["text_weight"] is not None else 0.5
            if type(weight) not in (float, int) or not fields["text"] or not 0.1 <= weight <= 0.9:
                raise ValueError("weight/text")
        except (TypeError, ValueError, AppError) as exc:
            raise AppError(422, "VALIDATION_ERROR", "Text hoặc trọng số không hợp lệ.") from exc
        return await search_result(
            request, lambda queries: queries.build_multimodal(fields["text"], blob, options, weight, mime)
        )

    @application.post("/api/v1/speech/transcriptions", openapi_extra=form_schema("audio", ["language"]))
    async def transcribe(request: Request):
        fields, blob, mime = await multipart(request, ("audio", "language"), "audio")
        if mime not in ("audio/wav", "audio/x-wav", "audio/wave"):
            raise AppError(415, "AUDIO_TYPE_UNSUPPORTED", "Chỉ nhận WAV PCM 16-bit mono 16 kHz.", "audio")
        result = await services(request).speech.transcribe(
            blob, fields["language"] if fields["language"] is not None else "vi-VN"
        )
        return {"request_id": request.state.request_id, **result}

    return application


app = create_app()
