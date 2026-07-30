"""API error types and the JSON error handlers that render them.

Every failure path in the service — validation, missing rows, bad routes and
unexpected crashes — leaves the app as a JSON body of the shape::

    {"error": "<machine_code>", "message": "<human text>", "details": {...}}

``details`` is only present when there is something field-specific to say.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Base class for failures that should be reported to the client as JSON."""

    status_code = 400
    error = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error is not None:
            self.error = error
        self.details = dict(details) if details else None

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.error, "message": self.message}
        if self.details:
            body["details"] = self.details
        return body


class ValidationError(ApiError):
    """The request body or query string did not pass validation."""

    status_code = 400
    error = "validation_failed"


class NotFoundError(ApiError):
    """The addressed resource does not exist."""

    status_code = 404
    error = "not_found"


class ConflictError(ApiError):
    """The request collides with an existing resource (e.g. a duplicate ISBN)."""

    status_code = 409
    error = "conflict"


def _code_for(exc: HTTPException) -> str:
    """Turn ``Method Not Allowed`` into ``method_not_allowed``."""
    name = exc.name or "http_error"
    return "_".join(name.lower().split())


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        # Reuse Werkzeug's response so headers it sets (e.g. ``Allow`` on a 405)
        # survive, and only swap the HTML body for JSON.
        response = exc.get_response()
        response.data = json.dumps(
            {
                "error": _code_for(exc),
                "message": exc.description or exc.name,
            }
        )
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        app.logger.exception("Unhandled error while serving request", exc_info=exc)
        return (
            jsonify(
                {
                    "error": "internal_server_error",
                    "message": "The server encountered an unexpected error.",
                }
            ),
            500,
        )
