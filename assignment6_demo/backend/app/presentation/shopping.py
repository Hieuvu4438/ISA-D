from fastapi import APIRouter, Request
from pydantic import Field, StrictBool, StrictInt

from app.domain import AppError, StrictModel
from app.presentation.accounts import identity


class CartUpdate(StrictModel):
    product_id: str = Field(strict=True, pattern=r"^P[0-9]{3}$")
    variant_id: str | None = Field(default=None, strict=True, pattern=r"^P[0-9]{3}(?:-[A-Z0-9]{1,8})?$")
    quantity: StrictInt = Field(ge=0, le=99)
    version: StrictInt = Field(ge=0, le=1_000_000_000)


class WishlistUpdate(StrictModel):
    product_id: str = Field(strict=True, pattern=r"^P[0-9]{3}$")
    saved: StrictBool


def mount_shopping(application, query_fields):
    router = APIRouter(prefix="/api/v1")

    def account(request, write=False):
        query_fields(request)
        if write:
            if request.headers.get("x-cortis-intent") != "commerce":
                raise AppError(403, "CSRF_REJECTED", "Hãy tải lại trang và thử lại.")
            if not request.headers.get("content-type", "").lower().startswith("application/json"):
                raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")
        return identity(request)

    @router.get("/cart")
    def cart(request: Request):
        return {"request_id": request.state.request_id, "cart": request.app.state.shopping.cart(account(request)["user_id"])}

    @router.post("/cart/items")
    def quantity(body: CartUpdate, request: Request):
        user = account(request, True)
        value = request.app.state.shopping.set_quantity(user["user_id"], body.product_id, body.quantity, body.version, expected_epoch=user["auth_epoch"], variant_id=body.variant_id)
        return {"request_id": request.state.request_id, "cart": value}

    @router.get("/wishlist")
    def wishlist(request: Request):
        return {"request_id": request.state.request_id, **request.app.state.shopping.wishlist(account(request)["user_id"])}

    @router.post("/wishlist/items")
    def save(body: WishlistUpdate, request: Request):
        user = account(request, True)
        value = request.app.state.shopping.save(user["user_id"], body.product_id, body.saved, expected_epoch=user["auth_epoch"])
        return {"request_id": request.state.request_id, **value}

    application.include_router(router)
