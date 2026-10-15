import re

from fastapi import APIRouter, Request
from pydantic import ValidationError

from app.domain import AppError, Filters


def mount_catalog(application, query_fields):
    router = APIRouter(prefix="/api/v1")

    def query_schema(suggestions=False):
        properties = {"q": {"type": "string", "maxLength": 500},
                      "limit": {"type": "integer", "minimum": 1, "maximum": 10 if suggestions else 100, "default": 6 if suggestions else 24}}
        properties["interpret_price"] = {"type": "boolean", "default": True}
        properties["interpret_exclusions"] = {"type": "boolean", "default": True}
        if not suggestions:
            properties.update({"offset": {"type": "integer", "minimum": 0, "maximum": 1_000_000, "default": 0},
                               "sort": {"type": "string", "enum": ["relevance", "price_asc", "price_desc", "name"], "default": "relevance"},
                               "category": {"type": "string"}, "brand": {"type": "string"}, "color": {"type": "string"}, "size": {"type": "string", "maxLength": 8},
                               "min_price": {"type": "integer", "minimum": 0, "maximum": 1_000_000_000},
                               "max_price": {"type": "integer", "minimum": 0, "maximum": 1_000_000_000},
                               "in_stock": {"type": "boolean", "default": False}})
        return {"parameters": [{"name": name, "in": "query", "required": False, "schema": schema} for name, schema in properties.items()]}

    def service(request):
        request.app.state.services.require("products")
        return request.app.state.services.catalog_search

    def number(request, name, default, minimum, maximum):
        value = request.query_params.get(name, str(default))
        if not re.fullmatch(r"[0-9]{1,10}", value) or not minimum <= int(value) <= maximum:
            raise AppError(422, "VALIDATION_ERROR", "Giá trị số không hợp lệ.", name)
        return int(value)

    @router.get("/catalog", openapi_extra=query_schema())
    def browse(request: Request):
        query_fields(request, ("q", "category", "brand", "color", "size", "min_price", "max_price", "in_stock", "sort", "offset", "limit", "interpret_price", "interpret_exclusions"))
        parse_exclusions = request.query_params.get("interpret_exclusions", "true")
        if parse_exclusions not in ("true", "false"):
            raise AppError(422, "VALIDATION_ERROR", "Tự hiểu loại trừ phải là true/false.", "interpret_exclusions")
        parse_price = request.query_params.get("interpret_price", "true")
        if parse_price not in ("true", "false"):
            raise AppError(422, "VALIDATION_ERROR", "Tự hiểu giá phải là true/false.", "interpret_price")
        values = {name: request.query_params[name] for name in ("category", "brand", "color", "size") if name in request.query_params}
        if any(not v.strip() for v in values.values()):
            raise AppError(422, "VALIDATION_ERROR", "Bộ lọc không được rỗng.")
        for name in ("min_price", "max_price"):
            if name in request.query_params:
                values[name] = number(request, name, 0, 0, 1_000_000_000)
        if "in_stock" in request.query_params:
            value = request.query_params["in_stock"]
            if value not in ("true", "false"):
                raise AppError(422, "VALIDATION_ERROR", "Trạng thái tồn kho phải là true/false.", "in_stock")
            values["in_stock"] = value == "true"
        try:
            filters = Filters.model_validate(values)
        except ValidationError as exc:
            raise AppError(422, "VALIDATION_ERROR", "Bộ lọc không hợp lệ.") from exc
        sort = request.query_params.get("sort", "relevance")
        if sort not in ("relevance", "price_asc", "price_desc", "name"):
            raise AppError(422, "VALIDATION_ERROR", "Cách sắp xếp không hợp lệ.", "sort")
        result = service(request).browse(request.query_params.get("q", ""), filters, sort,
                                         number(request, "offset", 0, 0, 1_000_000), number(request, "limit", 24, 1, 100), parse_price=parse_price == "true", parse_exclusions=parse_exclusions == "true")
        return {"request_id": request.state.request_id, **result}

    @router.get("/suggestions", openapi_extra=query_schema(True))
    def suggestions(request: Request):
        query_fields(request, ("q", "limit", "interpret_price", "interpret_exclusions"))
        parse_exclusions = request.query_params.get("interpret_exclusions", "true")
        if parse_exclusions not in ("true", "false"):
            raise AppError(422, "VALIDATION_ERROR", "Tự hiểu loại trừ phải là true/false.", "interpret_exclusions")
        parse_price = request.query_params.get("interpret_price", "true")
        if parse_price not in ("true", "false"):
            raise AppError(422, "VALIDATION_ERROR", "Tự hiểu giá phải là true/false.", "interpret_price")
        text = request.query_params.get("q", "")
        if len(text) > 500:
            raise AppError(422, "TEXT_TOO_LONG", "Mô tả tối đa 500 ký tự.", "q")
        return {"request_id": request.state.request_id,
                "products": service(request).suggestions(text, number(request, "limit", 6, 1, 10), parse_price=parse_price == "true", parse_exclusions=parse_exclusions == "true"), "retrieval": "lexical"}

    application.include_router(router)
