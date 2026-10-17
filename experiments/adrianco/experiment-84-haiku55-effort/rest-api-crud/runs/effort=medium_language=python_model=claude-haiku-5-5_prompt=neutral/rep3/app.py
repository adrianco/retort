"""REST API for managing a book collection, backed by SQLite."""

import os
import sqlite3
from datetime import date

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""

MAX_YEAR = date.today().year + 1


class ValidationError(Exception):
    """Raised when a request payload fails validation."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload):
    """Validate a book payload and return a cleaned dict.

    Raises ValidationError with a field -> message mapping on failure.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "request body must be a JSON object"})

    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if value is None:
            errors[field] = f"{field} is required"
        elif not isinstance(value, str) or not value.strip():
            errors[field] = f"{field} must be a non-empty string"
        else:
            cleaned[field] = value.strip()

    year = payload.get("year")
    if year is None:
        cleaned["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "year must be an integer"
    elif not 0 <= year <= MAX_YEAR:
        errors["year"] = f"year must be between 0 and {MAX_YEAR}"
    else:
        cleaned["year"] = year

    isbn = payload.get("isbn")
    if isbn is None:
        cleaned["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"
    else:
        cleaned["isbn"] = isbn.strip() or None

    if errors:
        raise ValidationError(errors)
    return cleaned


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or DEFAULT_DB_PATH

    # Initialise the schema once at startup.
    with sqlite3.connect(app.config["DATABASE"]) as conn:
        conn.executescript(SCHEMA)

    def get_db():
        if "db" not in g:
            conn = sqlite3.connect(app.config["DATABASE"])
            conn.row_factory = sqlite3.Row
            g.db = conn
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def fetch_book(book_id):
        return get_db().execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()

    def json_body():
        data = request.get_json(silent=True)
        if data is None:
            raise ValidationError({"body": "request body must be valid JSON"})
        return data

    def not_found():
        return jsonify(error="book not found"), 404

    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return jsonify(error="validation failed", details=err.errors), 400

    @app.errorhandler(404)
    def handle_404(_err):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def handle_405(_err):
        return jsonify(error="method not allowed"), 405

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        data = validate_book(json_body())
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        db.commit()
        book = fetch_book(cur.lastrowid)
        response = jsonify(row_to_dict(book))
        response.status_code = 201
        response.headers["Location"] = f"/books/{book['id']}"
        return response

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is not None:
            rows = get_db().execute(
                "SELECT id, title, author, year, isbn FROM books "
                "WHERE LOWER(author) = LOWER(?) ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = get_db().execute(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id"
            ).fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = fetch_book(book_id)
        if book is None:
            return not_found()
        return jsonify(row_to_dict(book))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        if fetch_book(book_id) is None:
            return not_found()
        data = validate_book(json_body())
        db = get_db()
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        db.commit()
        return jsonify(row_to_dict(fetch_book(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        if fetch_book(book_id) is None:
            return not_found()
        db = get_db()
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(debug=False)
