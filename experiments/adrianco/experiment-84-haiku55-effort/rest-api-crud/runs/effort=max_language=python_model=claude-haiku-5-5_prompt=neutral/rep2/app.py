"""REST API for managing a book collection, stored in SQLite.

Run with ``python app.py`` or ``flask --app app run``.
"""

import os
import sqlite3

from flask import Blueprint, Flask, current_app, g, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException, MethodNotAllowed, NotFound

import database
from validation import ValidationError, parse_author_filter, parse_book

# SQLite row ids are signed 64-bit integers, so a larger id can never match a book.
BOOK_ROUTE = "/books/<int(max=9223372036854775807):book_id>"

bp = Blueprint("books", __name__)


def get_db() -> sqlite3.Connection:
    """Return this request's database connection, opening it on first use."""
    if "db" not in g:
        g.db = database.connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _json_body() -> dict:
    # force=True accepts JSON sent without a Content-Type header.
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a JSON object.")
    return payload


@bp.get("/health")
def health():
    try:
        database.ping(get_db())
    except sqlite3.Error:
        return jsonify(status="error"), 503
    return jsonify(status="ok")


@bp.post("/books")
def create_book():
    book = database.insert_book(get_db(), parse_book(_json_body()))
    return jsonify(book), 201, {"Location": f"/books/{book['id']}"}


@bp.get("/books")
def list_books():
    author = parse_author_filter(request.args.get("author"))
    return jsonify(database.list_books(get_db(), author))


@bp.get(BOOK_ROUTE)
def get_book(book_id: int):
    book = database.get_book(get_db(), book_id)
    if book is None:
        raise NotFound(f"Book {book_id} not found.")
    return jsonify(book)


@bp.put(BOOK_ROUTE)
def update_book(book_id: int):
    # PUT replaces the whole book, so title and author are required on every update.
    book = database.update_book(get_db(), book_id, parse_book(_json_body()))
    if book is None:
        raise NotFound(f"Book {book_id} not found.")
    return jsonify(book)


@bp.delete(BOOK_ROUTE)
def delete_book(book_id: int):
    if not database.delete_book(get_db(), book_id):
        raise NotFound(f"Book {book_id} not found.")
    return "", 204


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify(error="Validation failed.", details=error.errors), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        response = jsonify(error=error.description)
        response.status_code = error.code
        if isinstance(error, MethodNotAllowed):
            response.headers["Allow"] = ", ".join(error.valid_methods or [])
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.error("Unhandled exception", exc_info=error)
        return jsonify(error="Internal server error."), 500


def create_app(database_path: str | None = None) -> Flask:
    """Build the app. The database path defaults to $BOOKS_DB_PATH, then ./books.db."""
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or os.environ.get(
        "BOOKS_DB_PATH", "books.db"
    )
    database.init_db(app.config["DATABASE"])

    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)
    _register_error_handlers(app)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
