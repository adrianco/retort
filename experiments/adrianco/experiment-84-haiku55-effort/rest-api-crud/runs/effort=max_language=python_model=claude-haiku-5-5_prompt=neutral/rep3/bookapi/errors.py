"""JSON error responses, so clients never receive Flask's HTML error pages."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException, MethodNotAllowed


class ApiError(Exception):
    """An error reported to the client as a JSON body with the given status code."""

    def __init__(self, status_code: int, message: str, details: dict[str, str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        body = {"error": err.message}
        if err.details:
            body["details"] = err.details
        return jsonify(body), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        response = jsonify(error=err.name)
        response.status_code = err.code
        if isinstance(err, MethodNotAllowed) and err.valid_methods:
            response.headers["Allow"] = ", ".join(err.valid_methods)
        return response
