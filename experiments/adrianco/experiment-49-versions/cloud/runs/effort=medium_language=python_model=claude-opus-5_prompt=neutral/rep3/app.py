"""REST API for managing a book collection.

Run locally with:

    python app.py

or with a WSGI server:

    gunicorn 'app:create_app()'
"""

import os
import sqlite3

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from db import close_db, get_db, init_db

DEFAULT_DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")

# Sanity bounds for the optional publication year.
MIN_YEAR = -3000
MAX_YEAR = 2100


class ValidationError(Exception):
    """Raised when a request payload fails validation."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def _row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _clean_string(value, field, errors, required):
    """Validate an optional/required string field, returning the cleaned value."""
    if value is None:
        if required:
            errors.append(f"{field} is required")
        return None
    if not isinstance(value, str):
        errors.append(f"{field} must be a string")
        return None
    value = value.strip()
    if not value:
        if required:
            errors.append(f"{field} must not be empty")
        return None
    return value


def _clean_year(value, errors):
    if value is None:
        return None
    # bool is a subclass of int, but True is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append("year must be an integer")
        return None
    if not MIN_YEAR <= value <= MAX_YEAR:
        errors.append(f"year must be between {MIN_YEAR} and {MAX_YEAR}")
        return None
    return value


def validate_book(payload):
    """Validate a create/update payload and return a normalised book dict."""
    if not isinstance(payload, dict):
        raise ValidationError(["request body must be a JSON object"])

    errors = []
    book = {
        "title": _clean_string(payload.get("title"), "title", errors, required=True),
        "author": _clean_string(payload.get("author"), "author", errors, required=True),
        "year": _clean_year(payload.get("year"), errors),
        "isbn": _clean_string(payload.get("isbn"), "isbn", errors, required=False),
    }
    if errors:
        raise ValidationError(errors)
    return book


def _json_body():
    """Parse the request body as JSON, raising ValidationError on bad input."""
    try:
        payload = request.get_json(silent=False)
    except HTTPException:
        payload = None
    if payload is None:
        raise ValidationError(
            ["request body must be valid JSON with Content-Type: application/json"]
        )
    return payload


def _fetch_book(book_id):
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return row


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", DEFAULT_DATABASE)
    app.teardown_appcontext(close_db)
    init_db(app)

    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return jsonify({"status": "error", "database": "unavailable"}), 503
        return jsonify({"status": "ok", "database": "ok"}), 200

    @app.post("/books")
    def create_book():
        book = validate_book(_json_body())
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book["title"], book["author"], book["year"], book["isbn"]),
        )
        db.commit()
        created = _row_to_book(_fetch_book(cur.lastrowid))
        return jsonify(created), 201, {"Location": f"/books/{created['id']}"}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        sql = "SELECT * FROM books"
        params = ()
        if author is not None:
            # Case-insensitive exact match on the author name.
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author.strip(),)
        sql += " ORDER BY id"
        rows = get_db().execute(sql, params).fetchall()
        return jsonify([_row_to_book(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = _fetch_book(book_id)
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(_row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        book = validate_book(_json_body())
        db = get_db()
        cur = db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book["title"], book["author"], book["year"], book["isbn"], book_id),
        )
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "book not found"}), 404
        return jsonify(_row_to_book(_fetch_book(book_id))), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "book not found"}), 404
        return "", 204

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc):
        return jsonify({"error": "validation failed", "details": exc.errors}), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        return jsonify({"error": exc.description}), exc.code

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
