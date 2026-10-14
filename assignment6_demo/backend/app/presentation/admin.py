import re
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field, StrictInt, field_validator

from app.domain import AppError, StrictModel, normalize_text
from app.presentation.accounts import identity


class ChangeReason(StrictModel):
    reason: str = Field(strict=True, min_length=3, max_length=200)

    @field_validator("reason")
    @classmethod
    def reason_valid(cls, value):
        value = normalize_text(value)
        if len(value) < 3 or any(ord(c) < 32 for c in value):
            raise ValueError("Hãy ghi lý do thay đổi")
        return value


class StockChange(ChangeReason):
    quantity: StrictInt = Field(ge=0, le=1_000_000)
    revision: StrictInt = Field(ge=0, le=1_000_000_000)


class RoleChange(ChangeReason):
    role: Literal["user", "admin"]
    version: StrictInt = Field(ge=0, le=1_000_000_000)


class OrderChange(ChangeReason):
    status: Literal["shipped", "delivered", "cancelled"]
    version: StrictInt = Field(ge=0, le=1_000_000_000)


class AccessChange(ChangeReason):
    access_state: Literal["active", "locked"]
    version: StrictInt = Field(ge=0, le=1_000_000_000)


def mount_admin(application, query_fields):
    router = APIRouter(prefix="/api/v1/admin")

    def page_schema(extra=None):
        params = [
            {"name": "offset", "in": "query", "schema": {"type": "integer", "minimum": 0, "maximum": 1_000_000, "default": 0}},
            {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
        ]
        if extra in ("q", "users"):
            params.append({"name": "q", "in": "query", "schema": {"type": "string", "maxLength": 120}})
        if extra == "users":
            params.append({"name": "access_state", "in": "query", "schema": {"type": "string", "enum": ["active", "locked"]}})
        if extra == "status":
            params.append({"name": "status", "in": "query", "schema": {"type": "string", "enum": ["processing", "shipped", "delivered", "cancelled"]}})
        return {"parameters": params}

    def actor(request, write=False):
        if write:
            query_fields(request)
            if request.headers.get("x-cortis-intent") != "admin":
                raise AppError(403, "CSRF_REJECTED", "Hãy tải lại trang và thử lại.")
            if not request.headers.get("content-type", "").lower().startswith("application/json"):
                raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")
        return identity(request, "admin")

    def pagination(request, extra=()):
        query_fields(request, ("offset", "limit", *extra))
        actor(request)
        values = {}
        for name, default, minimum, maximum in [("offset", 0, 0, 1_000_000), ("limit", 20, 1, 100)]:
            value = request.query_params.get(name, str(default))
            if not re.fullmatch(r"[0-9]{1,7}", value) or not minimum <= int(value) <= maximum:
                raise AppError(422, "VALIDATION_ERROR", "Phân trang không hợp lệ.", name)
            values[name] = int(value)
        return values

    @router.get("/inventory", openapi_extra=page_schema("q"))
    def inventory(request: Request):
        page = pagination(request, ("q",))
        query = request.query_params.get("q", "")
        if len(query) > 120:
            raise AppError(422, "VALIDATION_ERROR", "Từ khóa tối đa 120 ký tự.", "q")
        return {"request_id": request.state.request_id, **request.app.state.admin.inventory(**page, query=query)}

    @router.post("/inventory/{product_id}")
    def stock(product_id: str, body: StockChange, request: Request):
        admin = actor(request, True)
        if not re.fullmatch(r"P[0-9]{3}", product_id):
            raise AppError(422, "VALIDATION_ERROR", "Mã sản phẩm không hợp lệ.")
        return {"request_id": request.state.request_id, "inventory": request.app.state.admin.stock(admin["user_id"], product_id, body.quantity, body.revision, body.reason, expected_epoch=admin["auth_epoch"])}

    @router.get("/users", openapi_extra=page_schema("users"))
    def users(request: Request):
        page = pagination(request, ("q", "access_state"))
        query = request.query_params.get("q", "").strip()
        if len(query) > 120:
            raise AppError(422, "VALIDATION_ERROR", "Email tìm kiếm tối đa 120 ký tự.", "q")
        state = request.query_params.get("access_state")
        if state is not None and state not in ("active", "locked"):
            raise AppError(422, "VALIDATION_ERROR", "Trạng thái tài khoản không hợp lệ.", "access_state")
        return {"request_id": request.state.request_id, **request.app.state.admin.repository.users(**page, query=query, access_state=state)}

    @router.post("/users/{user_id}/role")
    def role(user_id: str, body: RoleChange, request: Request):
        admin = actor(request, True)
        if not re.fullmatch(r"[a-f0-9-]{36}", user_id):
            raise AppError(422, "VALIDATION_ERROR", "Mã tài khoản không hợp lệ.")
        return {"request_id": request.state.request_id, "user": request.app.state.admin.repository.role(admin["user_id"], user_id, body.role, body.version, body.reason, expected_epoch=admin["auth_epoch"])}

    @router.post("/users/{user_id}/access")
    def access(user_id: str, body: AccessChange, request: Request):
        admin = actor(request, True)
        if not re.fullmatch(r"[a-f0-9-]{36}", user_id):
            raise AppError(422, "VALIDATION_ERROR", "Mã tài khoản không hợp lệ.")
        return {"request_id": request.state.request_id, "user": request.app.state.admin.repository.access(admin["user_id"], user_id, body.access_state, body.version, body.reason, expected_epoch=admin["auth_epoch"])}

    @router.get("/purchases", openapi_extra=page_schema("status"))
    def orders(request: Request):
        page = pagination(request, ("status",))
        status = request.query_params.get("status")
        if status is not None and status not in ("processing", "shipped", "delivered", "cancelled"):
            raise AppError(422, "VALIDATION_ERROR", "Trạng thái không hợp lệ.")
        return {"request_id": request.state.request_id, **request.app.state.admin.repository.orders(**page, status=status)}

    @router.post("/purchases/{order_id}/status")
    def status(order_id: str, body: OrderChange, request: Request):
        admin = actor(request, True)
        if not re.fullmatch(r"ORD-[0-9A-F]{16}", order_id):
            raise AppError(422, "VALIDATION_ERROR", "Mã đơn hàng không hợp lệ.")
        return {"request_id": request.state.request_id, "order": request.app.state.admin.repository.transition(admin["user_id"], order_id, body.status, body.version, body.reason, expected_epoch=admin["auth_epoch"])}

    @router.get("/purchases/{order_id}")
    def detail(order_id: str, request: Request):
        query_fields(request)
        actor(request)
        if not re.fullmatch(r"ORD-[0-9A-F]{16}", order_id):
            raise AppError(422, "VALIDATION_ERROR", "Mã đơn hàng không hợp lệ.")
        return {"request_id": request.state.request_id, "order": request.app.state.admin.repository.order_detail(order_id)}

    @router.get("/audit", openapi_extra=page_schema())
    def audit(request: Request):
        page = pagination(request)
        return {"request_id": request.state.request_id, **request.app.state.admin.repository.audit_log(**page)}

    application.include_router(router)
