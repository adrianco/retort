"""Domain errors and the JSON error handlers that render them.

Every failure path in the service — validation, missing resources, conflicts,
routing errors raised by Werkzeug, and unexpected crashes — is rendered as JSON
so a client never has to parse an HTML error page.

The response body always has the same shape::

    {
      "error":   "validation_error",          # stable, machine-readable slug
      "message": "The request body failed ...",  # human-readable summary
      "details": {"title": "'title' is required."}   # optional, per-field
    }
"""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Base class for errors that map onto a JSON HTTP response."""

    status_code = 500
    code = "internal_error"
    message = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        self.details = details or {}

    def to_response(self) -> tuple[Response, int]:
        body: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.details:
            body["details"] = self.details
        return jsonify(body), self.status_code


class ValidationError(APIError):
    """The request body was missing, malformed, or failed field validation."""

    status_code = 400
    code = "validation_error"
    message = "The request body failed validation."


class NotFoundError(APIError):
    """The addressed resource does not exist."""

    status_code = 404
    code = "not_found"
    message = "The requested resource does not exist."


class ConflictError(APIError):
    """The request would violate a uniqueness constraint."""

    status_code = 409
    code = "conflict"
    message = "The request conflicts with an existing resource."


def register_error_handlers(app: Flask) -> None:
    """Install handlers that render every error as JSON."""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError) -> tuple[Response, int]:
        return error.to_response()

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
        # Covers routing-level failures Werkzeug raises before our code runs:
        # 404 for unknown paths, 405 for wrong methods, 413 for huge bodies.
        body = {
            "error": error.name.lower().replace(" ", "_"),
            "message": error.description,
        }
        return jsonify(body), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception) -> tuple[Response, int]:
        # Last resort: log the traceback for operators, but never leak internals
        # (stack traces, SQL, file paths) to the client.
        app.logger.exception("Unhandled exception while serving a request")
        return APIError().to_response()
