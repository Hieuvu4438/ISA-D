from fastapi import APIRouter, Request, Response
from pydantic import Field

from app.application.account_service import name_value
from app.domain import StrictModel, AppError

COOKIE = "cortis_session"


class LoginRequest(StrictModel):
    email: str = Field(strict=True, min_length=1, max_length=254)
    password: str = Field(strict=True, min_length=1, max_length=128)


class RegisterRequest(LoginRequest):
    display_name: str = Field(strict=True, min_length=1, max_length=80)


class ProfileRequest(StrictModel):
    display_name: str = Field(strict=True, min_length=1, max_length=80)


class PasswordRequest(StrictModel):
    current_password: str = Field(strict=True, min_length=1, max_length=128)
    password: str = Field(strict=True, min_length=15, max_length=128)


def account_service(request):
    return request.app.state.accounts


def identity(request, role=None):
    return account_service(request).require(request.cookies.get(COOKIE), role)


def mount_accounts(application, settings, query_fields):
    router = APIRouter(prefix="/api/v1")

    def check_write(request):
        query_fields(request)
        if request.headers.get("x-cortis-intent") != "account":
            raise AppError(403, "CSRF_REJECTED", "Yêu cầu chưa được xác nhận. Hãy tải lại trang và thử lại.")
        if not request.headers.get("content-type", "").lower().startswith("application/json"):
            raise AppError(415, "MEDIA_TYPE_UNSUPPORTED", "Cần gửi application/json.")

    def envelope(request, account):
        return {"request_id": request.state.request_id, "user": account_service(request).public(account)}

    def session(request, response, account):
        token = account_service(request).issue(account, request.cookies.get(COOKIE))
        response.set_cookie(COOKIE, token, max_age=8 * 3600, httponly=True, secure=settings.cookie_secure,
                            samesite="lax", path="/")
        return envelope(request, account)

    def peer(request):
        return request.client.host if request.client else "unknown"

    @router.post("/auth/register", status_code=201)
    def register(body: RegisterRequest, request: Request, response: Response):
        check_write(request)
        account = account_service(request).register(body.email, body.display_name, body.password, peer(request))
        return session(request, response, account)

    @router.post("/auth/login")
    def login(body: LoginRequest, request: Request, response: Response):
        check_write(request)
        return session(request, response, account_service(request).login(body.email, body.password, peer(request)))

    @router.get("/auth/me")
    def me(request: Request):
        query_fields(request)
        return envelope(request, identity(request))

    @router.post("/auth/logout")
    def logout(request: Request, response: Response):
        check_write(request)
        token = request.cookies.get(COOKIE)
        if token:
            account_service(request).repository.revoke(token)
        response.delete_cookie(COOKIE, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
        return {"request_id": request.state.request_id, "signed_out": True}

    @router.post("/account/profile")
    def profile(body: ProfileRequest, request: Request):
        check_write(request)
        account = identity(request)
        account["display_name"] = name_value(body.display_name)
        account_service(request).repository.update_name(account["user_id"], account["display_name"])
        return envelope(request, account)

    @router.post("/account/password")
    def password(body: PasswordRequest, request: Request, response: Response):
        check_write(request)
        account = identity(request)
        account_service(request).change_password(account, body.current_password, body.password, peer(request))
        return session(request, response, account)

    @router.get("/admin/overview")
    def overview(request: Request):
        query_fields(request)
        identity(request, "admin")
        services = request.app.state.services
        return {"request_id": request.state.request_id,
                "accounts": account_service(request).repository.counts(),
                "products": len(services.require("products").products),
                "orders": len(services.require("orders").orders)}

    application.include_router(router)
