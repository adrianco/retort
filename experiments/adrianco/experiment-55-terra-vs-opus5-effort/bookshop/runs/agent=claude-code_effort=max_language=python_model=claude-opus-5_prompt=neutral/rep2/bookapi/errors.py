"""Application errors and the JSON error handlers that render them.

Every failure that leaves this service - expected or not - is rendered as a
JSON object with a stable shape::

    {"error": "<human readable message>", "code": "<machine readable code>"}

Validation failures additionally carry a ``details`` object mapping each
offending field to the reason it was rejected.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Base class for errors that map onto an HTTP response.

    Subclasses fix the status and code as class attributes; a new failure mode
    means a new one-line subclass rather than per-call overrides.
    """

    status_code = 400
    code = "bad_request"

    def __init__(
        self, message: str, *, details: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details) if details else None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"error": self.message, "code": self.code}
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationError(ApiError):
    """The request was understood but its content is not acceptable."""

    status_code = 400
    code = "validation_error"


class NotFoundError(ApiError):
    """The addressed resource does not exist."""

    status_code = 404
    code = "not_found"


def _slugify(name: str) -> str:
    """Turn a Werkzeug exception name such as ``Not Found`` into ``not_found``."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "error"


def register_error_handlers(app: Flask) -> None:
    """Install handlers so the API never answers with an HTML error page."""

    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        # Start from Werkzeug's own response so status-specific headers such as
        # ``Allow`` on a 405 survive, then swap the HTML body for JSON.
        response = exc.get_response()
        payload = {
            "error": exc.description or exc.name,
            "code": _slugify(exc.name),
        }
        response.data = jsonify(payload).data
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        app.logger.exception("Unhandled error while serving a request", exc_info=exc)
        return (
            jsonify(
                {
                    "error": "The server encountered an internal error.",
                    "code": "internal_error",
                }
            ),
            500,
        )
