"""Error types and JSON error handlers.

Every failure leaves this service as JSON with the same envelope::

    {"error": {"code": "not_found", "message": "..."}}

Validation failures add a ``fields`` object mapping field name -> problem.
"""

from __future__ import annotations

from typing import Any, Mapping

from flask import Flask, current_app, json
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """An error that is safe to render back to the client."""

    status = 500
    code = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        fields: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status is not None:
            self.status = status
        if code is not None:
            self.code = code
        self.fields = dict(fields) if fields else None

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.fields:
            error["fields"] = self.fields
        return {"error": error}


class ValidationError(ApiError):
    status = 400
    code = "validation_error"


class NotFoundError(ApiError):
    status = 404
    code = "not_found"


class ConflictError(ApiError):
    status = 409
    code = "conflict"


class UnsupportedMediaTypeError(ApiError):
    status = 415
    code = "unsupported_media_type"


def _http_code(exc: HTTPException) -> str:
    """Turn ``Method Not Allowed`` into ``method_not_allowed``."""
    return (exc.name or "error").lower().replace(" ", "_").replace("-", "_")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        return exc.to_dict(), exc.status

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):
        # Reuse Werkzeug's response so headers such as ``Allow`` on a 405 and
        # ``Location`` on a redirect survive; only swap the HTML body for JSON.
        response = exc.get_response()
        payload = {"error": {"code": _http_code(exc), "message": exc.description}}
        response.set_data(json.dumps(payload))
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        current_app.logger.exception("Unhandled error while serving request")
        # Let tests and debug runs see the real traceback instead of a bland 500.
        # Registering this handler at all opts out of Flask's own propagation, so
        # resolve the setting the same way Flask would.
        propagate = current_app.config.get("PROPAGATE_EXCEPTIONS")
        if propagate is None:
            propagate = current_app.testing or current_app.debug
        if propagate:
            raise exc
        return (
            {"error": {"code": "internal_error", "message": "Internal server error."}},
            500,
        )
