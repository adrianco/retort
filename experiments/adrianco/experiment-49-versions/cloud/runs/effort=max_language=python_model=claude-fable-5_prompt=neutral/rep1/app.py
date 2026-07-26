"""A small REST API for managing a book collection, built on Flask + SQLite.

Run directly (``python3 app.py``) or via the Flask CLI (``flask --app app run``);
both use the ``create_app`` factory below.
"""

import os

from flask import Flask, jsonify, request, url_for
from werkzeug.exceptions import HTTPException

import db as database

ALLOWED_FIELDS = {"title", "author", "year", "isbn"}
REQUIRED_FIELDS = ("title", "author")


def json_error(message, status, details=None):
    """Build a consistent JSON error response."""
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def validate_book_payload(payload):
    """Validate a book payload and return ``(clean_data, field_errors)``.

    ``clean_data`` always contains all four columns (optional ones default to
    ``None``) so it can back both INSERT and full-replace UPDATE statements.
    """
    errors = {}

    for field in sorted(set(payload) - ALLOWED_FIELDS):
        errors[field] = "unknown field"

    clean = {}
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str) or not value.strip():
            errors[field] = "must be a non-empty string"
        else:
            clean[field] = value.strip()

    year = payload.get("year")
    if year is None:
        clean["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    else:
        clean["year"] = year

    isbn = payload.get("isbn")
    if isbn is None:
        clean["isbn"] = None
    elif not isinstance(isbn, str) or not isbn.strip():
        errors["isbn"] = "must be a non-empty string"
    else:
        clean["isbn"] = isbn.strip()

    return clean, errors


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_app(db_path=None):
    """Application factory. ``db_path`` overrides the ``BOOKS_DB`` env var."""
    app = Flask(__name__)
    app.config["DATABASE"] = str(
        db_path
        or os.environ.get("BOOKS_DB")
        or os.path.join(app.root_path, "books.db")
    )

    parent = os.path.dirname(app.config["DATABASE"])
    if parent:
        os.makedirs(parent, exist_ok=True)
    database.init_db(app.config["DATABASE"])
    app.teardown_appcontext(database.close_db)

    def parse_json_object():
        """Return the request body as a dict, or None if it isn't one."""
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else None

    def fetch_book(book_id):
        return database.get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()

    @app.get("/health")
    def health():
        database.get_db().execute("SELECT 1")
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        payload = parse_json_object()
        if payload is None:
            return json_error("request body must be a JSON object", 400)
        clean, errors = validate_book_payload(payload)
        if errors:
            return json_error("validation failed", 400, details=errors)

        conn = database.get_db()
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (clean["title"], clean["author"], clean["year"], clean["isbn"]),
        )
        conn.commit()

        book = book_to_dict(fetch_book(cursor.lastrowid))
        response = jsonify(book)
        response.status_code = 201
        response.headers["Location"] = url_for("get_book", book_id=book["id"])
        return response

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is not None:
            rows = database.get_db().execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = database.get_db().execute(
                "SELECT * FROM books ORDER BY id"
            ).fetchall()
        return jsonify([book_to_dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = fetch_book(book_id)
        if row is None:
            return json_error(f"book {book_id} not found", 404)
        return jsonify(book_to_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        payload = parse_json_object()
        if payload is None:
            return json_error("request body must be a JSON object", 400)
        clean, errors = validate_book_payload(payload)
        if errors:
            return json_error("validation failed", 400, details=errors)

        conn = database.get_db()
        cursor = conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (clean["title"], clean["author"], clean["year"], clean["isbn"], book_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return json_error(f"book {book_id} not found", 404)
        return jsonify(book_to_dict(fetch_book(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        conn = database.get_db()
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return json_error(f"book {book_id} not found", 404)
        return "", 204

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        # Framework-raised errors (unknown route, wrong method, wrapped 500s)
        # come back as JSON too, so API clients never see an HTML error page.
        return json_error(exc.name.lower(), exc.code or 500)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8000, debug=True)
