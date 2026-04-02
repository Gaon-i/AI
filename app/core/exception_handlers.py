from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.error_codes import HTTP_ERROR
from app.core.error_codes import INTERNAL_SERVER_ERROR
from app.core.error_codes import VALIDATION_ERROR
from app.core.exceptions import AppException
from app.schemas.common import ApiResponse


def _build_error_response(
    *,
    status_code: int,
    message: str,
    error_code: str,
    data: Any = None,
) -> JSONResponse:
    payload = ApiResponse[Any](
        status=status_code,
        message=message,
        data=data,
        error_code=error_code,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_, exc: AppException) -> JSONResponse:
        return _build_error_response(
            status_code=exc.error_code.status,
            message=exc.detail,
            error_code=exc.error_code.code,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(_, exc: RequestValidationError) -> JSONResponse:
        return _build_error_response(
            status_code=VALIDATION_ERROR.status,
            message=VALIDATION_ERROR.message,
            error_code=VALIDATION_ERROR.code,
            data={"errors": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else HTTP_ERROR.message
        return _build_error_response(
            status_code=exc.status_code,
            message=detail,
            error_code=HTTP_ERROR.code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_, __) -> JSONResponse:
        return _build_error_response(
            status_code=INTERNAL_SERVER_ERROR.status,
            message=INTERNAL_SERVER_ERROR.message,
            error_code=INTERNAL_SERVER_ERROR.code,
        )
