"""Error responses in the RFC 9457 "problem details" format.

Every error the API returns has the same JSON shape and the
``application/problem+json`` media type. That includes errors the framework
raises itself, such as 404 for unknown routes and 405 for unsupported methods.
"""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

from books_api.db import DatabaseUnavailable

PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    field: str
    message: str


class Problem(BaseModel):
    """RFC 9457 problem details. ``errors`` is present only on validation failures."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    errors: list[FieldError] | None = None


def problem_response(
    status: int,
    detail: str,
    *,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = Problem(
        title=HTTPStatus(status).phrase, status=status, detail=detail, errors=errors
    )
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=status,
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def _field_error(error: dict[str, Any]) -> FieldError:
    location = error["loc"]
    if tuple(location) == ("body",):  # the body as a whole, not one of its fields
        if error["type"] == "missing":
            return FieldError(field="body", message="Request body is required")
        return FieldError(field="body", message="Request body must be a JSON object")
    # ("body", "title") -> "title"
    return FieldError(field=".".join(str(part) for part in location[1:]), message=error["msg"])


_ROUTABLE_METHODS = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")


def _allowed_methods(request: Request) -> str:
    # Probe each method through the public Route.matches() rather than reading
    # route attributes: FastAPI wraps included routers in private objects.
    def routable(method: str) -> bool:
        scope = {**request.scope, "method": method}
        return any(route.matches(scope)[0] is Match.FULL for route in request.app.router.routes)

    return ", ".join(method for method in _ROUTABLE_METHODS if routable(method))


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    headers = exc.headers
    if exc.status_code == 405:
        # Starlette's Allow header names only the first route whose path
        # matched, but RFC 9110 requires every method the resource supports:
        # PATCH /books/1 must answer "GET, PUT, DELETE", not just "GET".
        headers = {**(headers or {}), "Allow": _allowed_methods(request)}
    return problem_response(exc.status_code, str(exc.detail), headers=headers)


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Messages are built from each error's location and text only. The raw
    # ``input`` is never echoed back: it can be bytes, which is not
    # JSON-serializable, and it repeats whatever the client sent.
    errors = exc.errors()
    for error in errors:
        if error["type"] == "json_invalid":
            reason = error.get("ctx", {}).get("error", "malformed JSON")
            return problem_response(400, f"Request body is not valid JSON: {reason}")
    return problem_response(
        400, "Request validation failed", errors=[_field_error(error) for error in errors]
    )


async def _database_unavailable(request: Request, exc: DatabaseUnavailable) -> JSONResponse:
    # For example "database is locked" beyond the busy timeout, or a database
    # file deleted while the server runs. Unlike a 500, nothing re-raises this,
    # so it is logged here.
    logger.warning(
        "Database unavailable for %s %s: %s", request.method, request.scope["path"], exc
    )
    return problem_response(503, "Database unavailable")


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Starlette re-raises the exception after this response is sent, so the
    # server still logs the traceback; the client never sees internal details.
    return problem_response(500, "An unexpected error occurred")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(DatabaseUnavailable, _database_unavailable)
    app.add_exception_handler(Exception, _unexpected_error)
