import re

from fastapi import APIRouter, Request
from pydantic import Field, StrictInt, field_validator

from app.domain import AppError, StrictModel, normalize_text
from app.presentation.accounts import identity


class ShippingAddress(StrictModel):
    recipient: str = Field(strict=True, min_length=2, max_length=80)
    phone: str = Field(strict=True, pattern=r"^(0[0-9]{9}|\+84[0-9]{9})$")
    address_line: str = Field(strict=True, min_length=5, max_length=250)
    city: str = Field(strict=True, min_length=2, max_length=80)

    @field_validator("recipient", "address_line", "city")
    @classmethod
    def clean_text(cls, value, info):
        value = normalize_text(value)
        if len(value) < (5 if info.field_name == "address_line" else 2) or any(ord(c) < 32 for c in value):
            raise ValueError("Thông tin địa chỉ không hợp lệ")
        return value


class PurchaseRequest(StrictModel):
    quote_id: str = Field(strict=True, min_length=20, max_length=100)
    idempotency_key: str = Field(strict=True, pattern=r"^[A-Za-z0-9-]{16,80}$")
    shipping_address: ShippingAddress


class VersionRequest(StrictModel):
    version: StrictInt = Field(ge=0, le=1_000_000_000)


class QuoteRequest(StrictModel):
    pass


def mount_purchases(application, query_fields):
    router = APIRouter(prefix="/api/v1")

    def account(request, write=False):
        query_fields(request)
        if write:
            if request.headers.get("x-cortis-intent") != "commerce":
                raise AppError(403, "CSRF_REJECTED", "Hãy tải lại trang và thử lại.")
            if not request.headers.get("content-type", "").lower().startswith("application/json"):
                raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")
        return identity(request)

    def order_id(value):
        if not re.fullmatch(r"ORD-[0-9A-F]{16}", value):
            raise AppError(422, "VALIDATION_ERROR", "Mã đơn hàng không hợp lệ.", "order_id")
        return value

    @router.post("/checkout/quote")
    def quote(body: QuoteRequest, request: Request):
        user = account(request, True)
        return {"request_id": request.state.request_id, "quote": request.app.state.purchases.quote(user["user_id"], expected_epoch=user["auth_epoch"])}

    @router.post("/purchases", status_code=201)
    def place(body: PurchaseRequest, request: Request):
        user = account(request, True)
        order, replayed = request.app.state.purchases.place(user["user_id"], body.quote_id, body.idempotency_key, body.shipping_address.model_dump(), expected_epoch=user["auth_epoch"])
        return {"request_id": request.state.request_id, "order": order, "replayed": replayed}

    @router.get("/purchases", openapi_extra={"parameters": [
        {"name": "offset", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 0, "maximum": 1_000_000, "default": 0}},
        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}},
    ]})
    def history(request: Request):
        query_fields(request, ("offset", "limit"))
        user_id = identity(request)["user_id"]
        values = {}
        for name, default, minimum, maximum in [("offset", 0, 0, 1_000_000), ("limit", 20, 1, 100)]:
            raw = request.query_params.get(name, str(default))
            if not re.fullmatch(r"[0-9]{1,7}", raw) or not minimum <= int(raw) <= maximum:
                raise AppError(422, "VALIDATION_ERROR", "Phân trang không hợp lệ.", name)
            values[name] = int(raw)
        return {"request_id": request.state.request_id, **request.app.state.purchases.repository.history(user_id, **values)}

    @router.get("/purchases/{purchase_id}")
    def detail(purchase_id: str, request: Request):
        return {"request_id": request.state.request_id, "order": request.app.state.purchases.repository.detail(account(request)["user_id"], order_id(purchase_id))}

    @router.post("/purchases/{purchase_id}/cancel")
    def cancel(purchase_id: str, body: VersionRequest, request: Request):
        user = account(request, True)
        return {"request_id": request.state.request_id, "order": request.app.state.purchases.repository.cancel(user["user_id"], order_id(purchase_id), body.version, expected_epoch=user["auth_epoch"])}

    application.include_router(router)
