"""REST API for managing a book collection.

Run with:  flask --app app run
"""

import os
import sqlite3

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from db import close_db, get_db, init_db

MIN_YEAR = -3000
MAX_YEAR = 2200


class ValidationError(Exception):
    """Raised when a request body fails validation."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def _clean_text(value, field, errors, required):
    """Validate an optional/required text field, returning the trimmed value."""
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
    """Validate a create/update payload and return normalized book fields."""
    if not isinstance(payload, dict):
        raise ValidationError(["request body must be a JSON object"])

    errors = []
    book = {
        "title": _clean_text(payload.get("title"), "title", errors, required=True),
        "author": _clean_text(payload.get("author"), "author", errors, required=True),
        "year": _clean_year(payload.get("year"), errors),
        "isbn": _clean_text(payload.get("isbn"), "isbn", errors, required=False),
    }
    if errors:
        raise ValidationError(errors)
    return book


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("DATABASE", "books.db")
    app.teardown_appcontext(close_db)

    @app.errorhandler(ValidationError)
    def _on_validation_error(exc):
        return jsonify(error="Validation failed", details=exc.errors), 400

    @app.errorhandler(HTTPException)
    def _on_http_error(exc):
        # Includes malformed JSON (400), unknown routes (404), bad method (405).
        return jsonify(error=exc.name, details=exc.description), exc.code

    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return jsonify(status="error", database="unavailable"), 503
        return jsonify(status="ok", database="ok"), 200

    @app.post("/books")
    def create_book():
        book = validate_book(request.get_json(silent=False))
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book["title"], book["author"], book["year"], book["isbn"]),
        )
        db.commit()
        created = _fetch(cur.lastrowid)
        return jsonify(created), 201, {"Location": f"/books/{created['id']}"}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        sql = "SELECT * FROM books"
        params = ()
        if author is not None:
            # Case-insensitive exact match on the trimmed author name.
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author.strip(),)
        sql += " ORDER BY id"
        rows = get_db().execute(sql, params).fetchall()
        return jsonify([dict(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = _fetch(book_id)
        if book is None:
            return _not_found(book_id)
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        book = validate_book(request.get_json(silent=False))
        db = get_db()
        cur = db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book["title"], book["author"], book["year"], book["isbn"], book_id),
        )
        db.commit()
        if cur.rowcount == 0:
            return _not_found(book_id)
        return jsonify(_fetch(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return _not_found(book_id)
        return "", 204

    init_db(app)
    return app


def _fetch(book_id):
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return dict(row) if row else None


def _not_found(book_id):
    return jsonify(error="Not Found", details=f"No book with id {book_id}"), 404


if __name__ == "__main__":
    # `flask --app app run` finds create_app() on its own; this is for `python app.py`.
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
