import re

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.domain import AppError
from app.domain.catalog_draft import DraftSave, DraftVersion, PhotoProvenance
from app.presentation.accounts import identity


def mount_catalog_drafts(application, query_fields, multipart, strict_json):
    router = APIRouter(prefix="/api/v1/admin")

    def actor(request, write=False, upload=False):
        if write:
            query_fields(request)
            if request.headers.get("x-cortis-intent") != "admin":
                raise AppError(403, "CSRF_REJECTED", "Hãy tải lại trang và thử lại.")
            if not upload and not request.headers.get("content-type", "").lower().startswith("application/json"):
                raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")
        return identity(request, "admin")

    def pid(value):
        if not re.fullmatch(r"P[0-9]{3}", value):
            raise AppError(422, "VALIDATION_ERROR", "Mã sản phẩm phải có dạng P001.", "product_id")
        return value

    def number(value, minimum=0, maximum=1_000_000_000):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,10}", value) or not minimum <= int(value) <= maximum:
            raise AppError(422, "VALIDATION_ERROR", "Phiên bản hoặc phân trang không hợp lệ.")
        return int(value)

    @router.get("/products", openapi_extra={"parameters": [
        {"name": "q", "in": "query", "schema": {"type": "string", "maxLength": 120}},
        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["draft", "live"]}},
        {"name": "offset", "in": "query", "schema": {"type": "integer", "minimum": 0, "maximum": 1_000_000, "default": 0}},
        {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
    ]})
    def listing(request: Request):
        query_fields(request, ("q", "status", "offset", "limit"))
        actor(request)
        q = request.query_params.get("q", "")
        status = request.query_params.get("status")
        if len(q) > 120 or status not in (None, "draft", "live"):
            raise AppError(422, "VALIDATION_ERROR", "Bộ lọc sản phẩm không hợp lệ.")
        result = request.app.state.catalog_drafts.listing(q, status, number(request.query_params.get("offset", "0"), maximum=1_000_000),
                                                         number(request.query_params.get("limit", "20"), minimum=1, maximum=100))
        return {"request_id": request.state.request_id, **result}

    @router.get("/products/{product_id}/draft")
    def detail(product_id: str, request: Request):
        query_fields(request)
        actor(request)
        return {"request_id": request.state.request_id, "draft": request.app.state.catalog_drafts.detail(pid(product_id))}

    @router.post("/products/{product_id}/draft")
    def save(product_id: str, body: DraftSave, request: Request):
        user = actor(request, True)
        result = request.app.state.catalog_drafts.save(user["user_id"], pid(product_id), body, user["auth_epoch"])
        return {"request_id": request.state.request_id, "draft": result}

    @router.post("/products/{product_id}/draft/discard")
    def discard(product_id: str, body: DraftVersion, request: Request):
        user = actor(request, True)
        result = request.app.state.catalog_drafts.discard(user["user_id"], pid(product_id), body.version, user["auth_epoch"])
        return {"request_id": request.state.request_id, "draft": result}

    @router.post("/products/{product_id}/draft/image", openapi_extra={"requestBody": {"required": True, "content": {
        "multipart/form-data": {"schema": {"type": "object", "required": ["image", "version", "provenance"], "properties": {
            "image": {"type": "string", "format": "binary"}, "version": {"type": "string", "pattern": "^[0-9]{1,10}$"},
            "provenance": {"type": "string", "description": "JSON PhotoProvenance: HTTPS sources, author, license, ISO date, real_photo_review=passed"},
        }}}}}})
    async def upload(product_id: str, request: Request):
        user = actor(request, True, upload=True)
        product_id = pid(product_id)
        fields, raw, content_type = await multipart(request, ("image", "version", "provenance"), "image")
        version = number(fields["version"])
        try:
            provenance = PhotoProvenance.model_validate(strict_json(fields["provenance"]))
        except (ValidationError, TypeError) as exc:
            raise AppError(422, "VALIDATION_ERROR", "Cần đầy đủ nguồn, tác giả, giấy phép, ngày lấy và xác nhận ảnh chụp thật.", "provenance") from exc
        service = request.app.state.catalog_drafts
        service.selected(product_id, version)
        info = await request.app.state.services.runner.run(lambda: service.prepare_image(raw, content_type))
        result = service.upload(user["user_id"], product_id, version, provenance, raw, info, user["auth_epoch"])
        return {"request_id": request.state.request_id, "draft": result}

    @router.get("/products/{product_id}/draft/image", openapi_extra={"parameters": [
        {"name": "v", "in": "query", "schema": {"type": "integer", "minimum": 0, "maximum": 1_000_000_000}},
    ]})
    def image(product_id: str, request: Request):
        query_fields(request, ("v",))
        actor(request)
        version = number(request.query_params["v"]) if "v" in request.query_params else None
        path, mime = request.app.state.catalog_drafts.image_file(pid(product_id), version)
        return FileResponse(path, media_type=mime)

    @router.post("/products/{product_id}/draft/preflight")
    async def preflight(product_id: str, body: DraftVersion, request: Request):
        user = actor(request, True)
        service = request.app.state.catalog_drafts
        product_id = pid(product_id)
        validation = await request.app.state.services.runner.run(lambda: service.preflight(product_id, body.version), request.app.state.services.settings.search_timeout)
        # A timed-out native call computes only; it cannot commit a late mutation.
        result = service.record_preflight(user["user_id"], product_id, body.version, validation, user["auth_epoch"])
        return {"request_id": request.state.request_id, "draft": result}

    @router.post("/products/{product_id}/draft/publish")
    async def publish(product_id: str, body: DraftVersion, request: Request):
        user = actor(request, True)
        publisher = request.app.state.catalog_publication
        prepared = await request.app.state.services.runner.run(lambda: publisher.prepare(pid(product_id), body.version), 30)
        async with request.app.state.catalog_gate.write():
            result = publisher.activate(request.app, prepared, user["user_id"], user["auth_epoch"])
        return {"request_id": request.state.request_id, "publication": result,
                "draft": request.app.state.catalog_drafts.detail(product_id)}

    application.include_router(router)
