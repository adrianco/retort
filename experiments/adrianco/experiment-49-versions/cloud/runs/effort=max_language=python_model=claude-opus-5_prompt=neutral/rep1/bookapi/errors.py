"""JSON error handling.

Flask's defaults render HTML error pages; an API should speak JSON for every
response it produces, including failures.  All errors share one shape::

    {"error": "<human readable message>", "details": [ ... ]}

where ``details`` is only present for validation failures and lists one entry
per offending field.
"""

from __future__ import annotations

import json

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

from .validation import ValidationError


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        response = jsonify({"error": exc.message, "details": exc.errors})
        response.status_code = 400
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException) -> Response:
        # Reuse the original response so status code and headers (``Allow`` on
        # a 405, for instance) survive; only swap the body for JSON.
        response = exc.get_response()
        response.data = json.dumps({"error": exc.description or exc.name})
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        # Let the test-suite see real tracebacks instead of a tidy 500.
        if app.config.get("TESTING"):
            raise exc
        app.logger.exception("Unhandled error while serving a request")
        response = jsonify({"error": "Internal server error"})
        response.status_code = 500
        return response
