"""Render every error as JSON, so clients never receive an HTML error page.

Error bodies look like ``{"error": "<message>"}``; validation failures add a
``details`` object mapping each invalid field to what is wrong with it.
"""

from __future__ import annotations

from typing import Any

from flask import Flask, current_app
from werkzeug.exceptions import HTTPException

from .validation import ValidationError


def register_error_handlers(app: Flask) -> None:
    app.register_error_handler(ValidationError, _validation_error)
    app.register_error_handler(HTTPException, _http_error)
    app.register_error_handler(Exception, _unexpected_error)


def _validation_error(error: ValidationError) -> Any:
    return {"error": "Validation failed", "details": error.errors}, 400


def _http_error(error: HTTPException) -> Any:
    # Keep the headers werkzeug attaches to the error, such as Allow on a 405,
    # but not its HTML Content-Type.
    headers = [(name, value) for name, value in error.get_headers()
               if name.lower() != "content-type"]
    return {"error": error.description}, error.code, headers


def _unexpected_error(error: Exception) -> Any:
    current_app.logger.error("Unhandled exception", exc_info=error)
    return {"error": "Internal server error"}, 500
