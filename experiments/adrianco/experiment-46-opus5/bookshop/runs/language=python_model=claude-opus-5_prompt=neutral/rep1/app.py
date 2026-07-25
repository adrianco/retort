"""A small REST API for managing a book collection.

Run with:
    flask --app app run          # development server
    python app.py                # equivalent, honours PORT
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Mapping

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

import db
import repository
from validation import ValidationError, validate_book

DEFAULT_DATABASE = "books.db"


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build the application. ``config`` overrides values such as ``DATABASE``."""
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("BOOKS_DATABASE", DEFAULT_DATABASE)
    if config:
        app.config.update(config)
    app.json.sort_keys = False

    db.register(app)
    with app.app_context():
        db.init_db()

    _register_routes(app)
    _register_error_handlers(app)
    return app


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _error(status: int, message: str, **extra: Any):
    return jsonify({"error": message, **extra}), status


def _json_object() -> Any:
    """Return the parsed request body, or raise ValidationError if unusable.

    ``force=True`` means a missing or wrong ``Content-Type`` is tolerated; the
    body still has to be valid JSON.
    """
    body = request.get_json(silent=True, force=True)
    if body is None:
        raise ValidationError({"body": "Request body must be valid JSON"})
    return body


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


def _register_routes(app: Flask) -> None:
    @app.get("/health")
    def health():
        """Liveness plus a real round-trip to the database."""
        try:
            db.get_db().execute("SELECT 1").fetchone()
        except sqlite3.Error as exc:
            return _error(503, "Database unavailable", detail=str(exc))
        return jsonify({"status": "ok", "database": "ok"}), 200

    @app.post("/books")
    def create_book():
        book = validate_book(_json_object())
        created = repository.create(db.get_db(), book)
        return jsonify(created), 201, {"Location": f"/books/{created['id']}"}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        books = repository.list_all(db.get_db(), author=author)
        return jsonify(books), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        book = repository.get(db.get_db(), book_id)
        if book is None:
            return _error(404, f"No book with id {book_id}")
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        book = validate_book(_json_object())
        updated = repository.replace(db.get_db(), book_id, book)
        if updated is None:
            return _error(404, f"No book with id {book_id}")
        return jsonify(updated), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        if not repository.delete(db.get_db(), book_id):
            return _error(404, f"No book with id {book_id}")
        return "", 204


# --------------------------------------------------------------------------- #
# Error handling — every failure is reported as JSON, never HTML
# --------------------------------------------------------------------------- #


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return _error(400, "Validation failed", details=exc.errors)

    @app.errorhandler(repository.DuplicateISBNError)
    def handle_duplicate_isbn(exc: repository.DuplicateISBNError):
        return _error(409, str(exc))

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        return _error(exc.code or 500, exc.description or exc.name)

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        # Under TESTING/DEBUG, let it propagate so the real traceback surfaces
        # instead of a tidy 500 body.
        if app.config.get("PROPAGATE_EXCEPTIONS") or app.testing or app.debug:
            raise exc
        app.logger.exception("Unhandled error while serving %s", request.path)
        return _error(500, "Internal server error")


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    create_app({"DEBUG": debug}).run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
