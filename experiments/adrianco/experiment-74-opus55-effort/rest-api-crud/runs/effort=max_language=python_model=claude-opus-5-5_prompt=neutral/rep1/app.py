"""Book collection REST API: Flask routes over a SQLite database."""

import os
import sqlite3
from typing import Any, NoReturn

from flask import Blueprint, Flask, abort, jsonify, request, url_for
from werkzeug.exceptions import BadRequest, HTTPException

import db
from validation import ValidationError, validate_book

BOOK_URL = "/books/<int:book_id>"

api = Blueprint("api", __name__)


def create_app(config: dict[str, Any] | None = None) -> Flask:
    """Application factory; *config* overrides the defaults (tests use this)."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "BOOKS_DB_PATH", os.path.join(app.instance_path, "books.db")
        ),
        # Book payloads are tiny; anything bigger than this is refused with 413.
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if config:
        app.config.update(config)
    app.json.sort_keys = False  # keep fields in model order: id, title, ...

    db.init_app(app)
    app.register_blueprint(api)
    app.register_error_handler(ValidationError, _validation_error)
    app.register_error_handler(HTTPException, _http_error)
    return app


@api.get("/health")
def health():
    try:
        db.ping()
    except sqlite3.Error:
        return jsonify(status="error", database="unavailable"), 503
    return jsonify(status="ok", database="ok")


@api.get("/books")
def list_books():
    author = request.args.get("author", "").strip()
    return jsonify(db.list_books(author=author or None))


@api.post("/books")
def create_book():
    book = db.create_book(validate_book(_json_body()))
    location = url_for(".get_book", book_id=book["id"])
    return jsonify(book), 201, {"Location": location}


@api.get(BOOK_URL)
def get_book(book_id: int):
    book = db.get_book(book_id)
    if book is None:
        _not_found(book_id)
    return jsonify(book)


@api.put(BOOK_URL)
def update_book(book_id: int):
    book = db.update_book(book_id, validate_book(_json_body()))
    if book is None:
        _not_found(book_id)
    return jsonify(book)


@api.delete(BOOK_URL)
def delete_book(book_id: int):
    if not db.delete_book(book_id):
        _not_found(book_id)
    return jsonify(id=book_id, deleted=True)


def _json_body() -> Any:
    """The decoded JSON body; 415 if it is not JSON, 400 if it is malformed."""
    try:
        return request.get_json()
    except BadRequest:
        abort(400, description="Request body is not valid JSON")


def _not_found(book_id: int) -> NoReturn:
    abort(404, description=f"Book {book_id} not found")


def _validation_error(error: ValidationError):
    body: dict[str, Any] = {"error": str(error)}
    if error.details:
        body["details"] = error.details
    return jsonify(body), 400


def _http_error(error: HTTPException):
    """Render HTTP errors (404, 405, 413, 415, 500, ...) as JSON."""
    response = error.get_response()  # keeps headers such as Allow on a 405
    response.set_data(jsonify(error=error.description).get_data())
    response.content_type = "application/json"
    return response


def main() -> None:
    """Serve with Flask's built-in server; HOST and PORT come from the environment."""
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    main()
