"""A small REST API for managing a book collection.

Flask + SQLite (stdlib ``sqlite3``). Run with ``python app.py`` or via any WSGI
server pointing at ``app:create_app()``.
"""

import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from db import close_db, get_db, init_db

BOOK_FIELDS = ("title", "author", "year", "isbn")


class ValidationError(Exception):
    """Raised when a request body fails validation."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def _clean_str(value):
    return value.strip() if isinstance(value, str) else value


def validate_book(payload, partial=False):
    """Validate a book payload and return the cleaned field dict.

    ``title`` and ``author`` are required and must be non-empty strings. With
    ``partial=True`` (PATCH-style semantics) absent fields are simply omitted,
    but any field that *is* present still has to be valid.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "expected a JSON object"})

    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        if field not in payload:
            if not partial:
                errors[field] = "field is required"
            continue
        value = _clean_str(payload[field])
        if not isinstance(value, str) or not value:
            errors[field] = "must be a non-empty string"
        else:
            cleaned[field] = value

    if "year" in payload:
        year = payload["year"]
        if year is None:
            cleaned["year"] = None
        elif isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "must be an integer or null"
        elif not 0 <= year <= 2200:
            errors["year"] = "must be between 0 and 2200"
        else:
            cleaned["year"] = year
    elif not partial:
        cleaned["year"] = None

    if "isbn" in payload:
        isbn = _clean_str(payload["isbn"])
        if isbn is None or isbn == "":
            cleaned["isbn"] = None
        elif not isinstance(isbn, str):
            errors["isbn"] = "must be a string or null"
        else:
            cleaned["isbn"] = isbn
    elif not partial:
        cleaned["isbn"] = None

    unknown = sorted(set(payload) - set(BOOK_FIELDS))
    if unknown:
        errors["_unknown"] = f"unknown field(s): {', '.join(unknown)}"

    if errors:
        raise ValidationError(errors)
    return cleaned


def row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", "books.db")
    app.teardown_appcontext(close_db)
    init_db(app)

    # ---- error handling ------------------------------------------------
    @app.errorhandler(ValidationError)
    def _on_validation_error(exc):
        return jsonify(error="Validation failed", details=exc.errors), 400

    @app.errorhandler(HTTPException)
    def _on_http_error(exc):
        return jsonify(error=exc.name, details=exc.description), exc.code

    def json_body():
        """Parse the request body as JSON, rejecting anything malformed."""
        body = request.get_json(silent=True)
        if body is None:
            raise ValidationError({"body": "a JSON object body is required"})
        return body

    # ---- routes -------------------------------------------------------
    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
        except Exception as exc:  # pragma: no cover - defensive
            return jsonify(status="error", database="unavailable", details=str(exc)), 503
        return jsonify(status="ok", database="ok"), 200

    @app.post("/books")
    def create_book():
        data = validate_book(json_body())
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        book = row_to_book(row)
        return jsonify(book), 201, {"Location": f"/books/{book['id']}"}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        sql = "SELECT * FROM books"
        params = ()
        if author is not None:
            # Case-insensitive exact match on author.
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author.strip(),)
        sql += " ORDER BY id"
        rows = get_db().execute(sql, params).fetchall()
        return jsonify([row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify(error="Not Found", details=f"no book with id {book_id}"), 404
        return jsonify(row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = validate_book(json_body())
        db = get_db()
        cur = db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        db.commit()
        if cur.rowcount == 0:
            return jsonify(error="Not Found", details=f"no book with id {book_id}"), 404
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify(error="Not Found", details=f"no book with id {book_id}"), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
