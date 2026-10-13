from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging_setup import get_logger

log = get_logger("raaz.errors")


class DomainError(Exception):
    """A predictable, player-safe error. `code` is machine readable; `message` is shown to the player."""

    status = 400

    def __init__(self, code: str, message: str, *, status: int | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        if status is not None:
            self.status = status


class NotFound(DomainError):
    status = 404

    def __init__(self, what: str = "resource", message: str | None = None):
        super().__init__("not_found", message or f"{what} not found")


class Forbidden(DomainError):
    status = 403

    def __init__(self, code: str = "forbidden", message: str = "You cannot do that."):
        super().__init__(code, message)


class Conflict(DomainError):
    status = 409

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(code, message, details=details)


class TooManyRequests(DomainError):
    status = 429

    def __init__(self, message: str = "Too many requests. Slow down, Inspector.", retry_after: int = 30):
        super().__init__("rate_limited", message, details={"retry_after": retry_after})


def _body(code: str, message: str, details: dict[str, Any] | None = None, request_id: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}, "request_id": request_id}}


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError):
        headers = {}
        if isinstance(exc, TooManyRequests):
            headers["Retry-After"] = str(exc.details.get("retry_after", 30))
        return JSONResponse(
            _body(exc.code, exc.message, exc.details, getattr(request.state, "request_id", None)),
            status_code=exc.status, headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errs = [{"loc": [str(x) for x in e["loc"]], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(
            _body("validation_error", "The request was not valid.", {"errors": errs}, getattr(request.state, "request_id", None)),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            _body("http_error", str(exc.detail), None, getattr(request.state, "request_id", None)),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error", extra={"path": request.url.path})
        return JSONResponse(
            _body("internal_error", "Something went wrong on our side.", None, getattr(request.state, "request_id", None)),
            status_code=500,
        )
