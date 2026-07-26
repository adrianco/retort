"""Error type and handlers that keep every failure response JSON."""

from __future__ import annotations

from typing import Any

from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """An error that should be rendered as a JSON response body."""

    def __init__(
        self,
        status: int,
        error: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.error = error
        self.message = message
        self.details = details

    def to_response(self):
        payload: dict[str, Any] = {"error": self.error, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return jsonify(payload), self.status


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        return exc.to_response()

    @app.errorhandler(HTTPException)
    def _handle_http_error(exc: HTTPException):
        # Werkzeug renders HTML by default (404s on unknown routes, 405s, ...);
        # re-render them as JSON so clients only ever have to parse one format.
        error = exc.name.lower().replace(" ", "_")
        return ApiError(exc.code or 500, error, exc.description or exc.name).to_response()

    @app.errorhandler(Exception)
    def _handle_unexpected_error(exc: Exception):
        app.logger.exception("unhandled error while serving request", exc_info=exc)
        return ApiError(
            500, "internal_server_error", "The server encountered an unexpected error."
        ).to_response()
