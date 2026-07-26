"""Application errors and the JSON error handlers that render them.

Every failure leaves the API as a JSON document with the same shape::

    {"error": "<machine code>", "message": "<human readable>", "details": {...}}

``details`` is only present when a handler has field-level information to add.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional

from flask import Flask, current_app, jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Base class for errors that should be rendered as a JSON response."""

    status_code = 500
    code = "internal_error"
    message = "An unexpected internal error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details: Dict[str, Any] = dict(details or {})

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"error": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationError(ApiError):
    """The request payload or query string could not be accepted."""

    status_code = 400
    code = "validation_error"
    message = "The request could not be validated."


class NotFoundError(ApiError):
    """The addressed resource does not exist."""

    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(ApiError):
    """The request conflicts with the current state of the collection."""

    status_code = 409
    code = "conflict"
    message = "The request conflicts with an existing resource."


def _code_for_status(status: Optional[int]) -> str:
    """Turn an HTTP status into a snake_case machine code (404 -> not_found)."""
    try:
        phrase = HTTPStatus(int(status)).phrase  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return "error"
    return phrase.lower().replace("-", " ").replace(" ", "_")


def register_error_handlers(app: Flask) -> None:
    """Attach the JSON error handlers to ``app``."""

    @app.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        response = jsonify(exc.to_dict())
        response.status_code = exc.status_code
        return response

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):
        status = exc.code or 500
        response = jsonify(
            {
                "error": _code_for_status(status),
                "message": exc.description or HTTPStatus(status).phrase,
            }
        )
        response.status_code = status
        # Preserve protocol headers Werkzeug computed for us, e.g. the "Allow"
        # header that must accompany a 405 response.
        original = exc.get_response()
        for header in ("Allow", "WWW-Authenticate", "Retry-After"):
            if header in original.headers:
                response.headers[header] = original.headers[header]
        return response

    @app.errorhandler(Exception)
    def _handle_unexpected_error(exc: Exception):
        if isinstance(exc, (ApiError, HTTPException)):  # pragma: no cover - safety net
            raise exc
        # Let the traceback surface while developing or running the test suite.
        if current_app.debug or current_app.testing:
            raise exc
        current_app.logger.exception("Unhandled error while serving a request")
        response = jsonify(
            {
                "error": "internal_error",
                "message": "An unexpected internal error occurred.",
            }
        )
        response.status_code = 500
        return response
