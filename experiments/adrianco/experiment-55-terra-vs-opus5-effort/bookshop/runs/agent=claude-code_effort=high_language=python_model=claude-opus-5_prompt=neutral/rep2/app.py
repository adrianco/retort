"""A small REST API for managing a book collection.

Development server:
    python app.py

Application factory (for gunicorn/waitress):
    gunicorn "app:create_app()"
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import Flask, jsonify, request, url_for
from werkzeug.exceptions import HTTPException

import database
import validation

DEFAULT_DATABASE = "books.db"


class ApiError(Exception):
    """An error to report to the client as JSON."""

    def __init__(self, status: int, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def create_app(database_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = (
        database_path or os.environ.get("BOOKS_DATABASE") or DEFAULT_DATABASE
    )
    app.json.sort_keys = False  # preserve the field order we build responses in

    database.init_app(app)
    _register_routes(app)
    _register_error_handlers(app)
    return app


def _register_routes(app: Flask) -> None:
    @app.get("/health")
    def health():
        try:
            database.ping()
        except sqlite3.Error as exc:
            return jsonify(status="unhealthy", database=str(exc)), 503
        return jsonify(status="ok", database="ok")

    @app.post("/books")
    def create_book():
        data = validation.parse_book(_json_body())
        book = database.insert_book(data)
        location = url_for("get_book", book_id=book["id"])
        return jsonify(book), 201, {"Location": location}

    @app.get("/books")
    def list_books():
        author = (request.args.get("author") or "").strip()
        return jsonify(database.list_books(author or None))

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        return jsonify(_require_book(book_id))

    @app.put("/books/<int:book_id>")
    def replace_book(book_id: int):
        # PUT replaces the whole resource: fields left out are cleared.
        data = validation.parse_book(_json_body())
        book = database.update_book(book_id, data)
        if book is None:
            raise _not_found(book_id)
        return jsonify(book)

    @app.patch("/books/<int:book_id>")
    def patch_book(book_id: int):
        # Convenience alongside PUT: update only the fields supplied.
        data = validation.parse_book(_json_body(), partial=True)
        book = database.update_book(book_id, data)
        if book is None:
            raise _not_found(book_id)
        return jsonify(book)

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        if not database.delete_book(book_id):
            raise _not_found(book_id)
        return "", 204


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(validation.ValidationError)
    def _on_validation_error(exc: validation.ValidationError):
        return jsonify(error="validation failed", details=exc.errors), 400

    @app.errorhandler(database.DuplicateISBN)
    def _on_duplicate_isbn(exc: database.DuplicateISBN):
        return jsonify(error=str(exc), details={"isbn": "must be unique"}), 409

    @app.errorhandler(ApiError)
    def _on_api_error(exc: ApiError):
        body: dict[str, Any] = {"error": exc.message}
        if exc.details is not None:
            body["details"] = exc.details
        return jsonify(body), exc.status

    @app.errorhandler(HTTPException)
    def _on_http_error(exc: HTTPException):
        # Flask's stock 404/405/... pages are HTML; this API answers in JSON.
        return jsonify(error=exc.description, status=exc.code), exc.code or 500

    @app.errorhandler(sqlite3.Error)
    def _on_database_error(exc: sqlite3.Error):
        app.logger.exception("database failure")
        return jsonify(error="database error"), 500


def _json_body() -> Any:
    if not request.is_json:
        raise ApiError(415, "Content-Type must be application/json")
    body = request.get_json(silent=True)
    if body is None:
        raise ApiError(400, "request body must be a JSON object")
    return body


def _require_book(book_id: int) -> dict[str, Any]:
    book = database.get_book(book_id)
    if book is None:
        raise _not_found(book_id)
    return book


def _not_found(book_id: int) -> ApiError:
    return ApiError(404, f"book {book_id} not found")


if __name__ == "__main__":  # pragma: no cover - manual entry point
    create_app().run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
