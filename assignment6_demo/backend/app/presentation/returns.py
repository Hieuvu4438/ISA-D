import re
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field, StrictInt, model_validator

from app.domain import AppError, StrictModel
from app.presentation.accounts import identity
from app.presentation.admin import ChangeReason
from app.presentation.purchases import VersionRequest
from app.data.return_repository import STATUSES


class ReturnItem(StrictModel):
    product_id: str = Field(strict=True, pattern=r"^P[0-9]{3}$")
    quantity: StrictInt = Field(ge=1, le=99)


class ReturnRequest(ChangeReason):
    version: StrictInt = Field(ge=0, le=1_000_000_000)
    idempotency_key: str = Field(strict=True, pattern=r"^[A-Za-z0-9-]{16,80}$")
    items: list[ReturnItem] = Field(min_length=1, max_length=100)


class ReceiptItem(StrictModel):
    product_id: str = Field(strict=True, pattern=r"^P[0-9]{3}$")
    restock_quantity: StrictInt = Field(ge=0, le=99)


class ReturnTransition(ChangeReason):
    status: Literal["approved", "rejected", "received", "closed"]
    version: StrictInt = Field(ge=0, le=1_000_000_000)
    receipt: list[ReceiptItem] | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def receipt_for_receiving(self):
        if (self.status == "received") != (self.receipt is not None):
            raise ValueError("Chỉ nhận hàng cần kết quả kiểm tra từng sản phẩm")
        return self


def mount_returns(application, query_fields):
    router = APIRouter(prefix="/api/v1")

    def actor(request, admin=False, write=False):
        if write:
            query_fields(request)
            if request.headers.get("x-cortis-intent") != ("admin" if admin else "commerce"):
                raise AppError(403, "CSRF_REJECTED", "Hãy tải lại trang và thử lại.")
            if not request.headers.get("content-type", "").lower().startswith("application/json"):
                raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")
        return identity(request, "admin" if admin else None)

    def identifier(value, prefix):
        if not re.fullmatch(prefix + r"-[A-F0-9]{16}", value):
            raise AppError(422, "VALIDATION_ERROR", "Mã đơn hoặc yêu cầu trả hàng không hợp lệ.")
        return value

    @router.get("/purchases/{purchase_id}/returns")
    def order_returns(purchase_id: str, request: Request):
        query_fields(request)
        return {"request_id": request.state.request_id, **request.app.state.returns.order_returns(actor(request)["user_id"], identifier(purchase_id, "ORD"))}

    @router.post("/purchases/{purchase_id}/returns", status_code=201)
    def create(purchase_id: str, body: ReturnRequest, request: Request):
        user = actor(request, write=True)
        result, replayed = request.app.state.returns.create(user["user_id"], identifier(purchase_id, "ORD"), body.version,
                                                          body.idempotency_key, [i.model_dump() for i in body.items], body.reason, expected_epoch=user["auth_epoch"])
        return {"request_id": request.state.request_id, "return": result, "replayed": replayed}

    @router.post("/returns/{return_id}/withdraw")
    def withdraw(return_id: str, body: VersionRequest, request: Request):
        user = actor(request, write=True)
        return {"request_id": request.state.request_id, "return": request.app.state.returns.withdraw(user["user_id"], identifier(return_id, "RMA"), body.version, expected_epoch=user["auth_epoch"])}

    @router.get("/admin/returns", openapi_extra={"parameters": [
        {"name": "offset", "in": "query", "schema": {"type": "integer", "minimum": 0, "maximum": 1_000_000, "default": 0}},
        {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
        {"name": "status", "in": "query", "schema": {"type": "string", "enum": list(STATUSES)}},
    ]})
    def listing(request: Request):
        query_fields(request, ("offset", "limit", "status"))
        actor(request, admin=True)
        values = {}
        for name, default, minimum, maximum in [("offset", 0, 0, 1_000_000), ("limit", 20, 1, 100)]:
            raw = request.query_params.get(name, str(default))
            if not re.fullmatch(r"[0-9]{1,7}", raw) or not minimum <= int(raw) <= maximum:
                raise AppError(422, "VALIDATION_ERROR", "Phân trang không hợp lệ.", name)
            values[name] = int(raw)
        status = request.query_params.get("status")
        if status is not None and status not in STATUSES:
            raise AppError(422, "VALIDATION_ERROR", "Trạng thái trả hàng không hợp lệ.", "status")
        return {"request_id": request.state.request_id, **request.app.state.returns.listing(**values, status=status)}

    @router.post("/admin/returns/{return_id}/status")
    def transition(return_id: str, body: ReturnTransition, request: Request):
        user = actor(request, admin=True, write=True)
        result = request.app.state.returns.transition(user["user_id"], identifier(return_id, "RMA"), body.status,
                                                     body.version, body.reason, [i.model_dump() for i in body.receipt] if body.receipt else None, expected_epoch=user["auth_epoch"])
        return {"request_id": request.state.request_id, "return": result}

    application.include_router(router)
