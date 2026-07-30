"""JSON error responses.

Flask serves HTML error pages by default; these handlers make every failure --
including 404s on unknown routes and 405s -- come back as JSON.
"""

from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .validation import ValidationError


def json_error(status: int, message: str, details: dict | None = None):
    """Build a ``({"error": ..., "details": ...}, status)`` response."""
    payload: dict[str, object] = {"error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def _validation_error(exc: ValidationError):
        return json_error(400, exc.message, exc.errors)

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        # Prefer a description we set ourselves via abort(); fall back to the
        # short status name rather than Werkzeug's verbose stock prose.
        if exc.description and exc.description != type(exc).description:
            message = exc.description
        else:
            message = exc.name
        return json_error(exc.code or 500, message)

    @app.errorhandler(Exception)
    def _unexpected_error(exc: Exception):
        if app.config.get("TESTING"):
            # Surface the traceback to the test runner instead of hiding it.
            raise exc
        app.logger.exception("Unhandled error while serving request")
        return json_error(500, "Internal server error")
