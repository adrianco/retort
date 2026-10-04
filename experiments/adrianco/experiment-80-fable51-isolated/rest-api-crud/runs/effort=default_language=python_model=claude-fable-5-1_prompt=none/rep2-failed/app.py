"""Book collection REST API backed by SQLite."""

import os
import sqlite3

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
)
"""


def validate_book(data):
    """Return (clean_fields, errors) for a book payload."""
    if not isinstance(data, dict):
        return None, ["request body must be a JSON object"]

    errors = []
    clean = {}

    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} is required and must be a non-empty string")
        else:
            clean[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, so reject it explicitly
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    clean["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
        errors.append("isbn must be a non-empty string")
    clean["isbn"] = isbn.strip() if isinstance(isbn, str) else None

    return clean, errors


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("BOOKS_DB", "books.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().execute(SCHEMA)
        get_db().commit()

    def error(message, status, **extra):
        return jsonify({"error": message, **extra}), status

    def fetch_book(book_id):
        row = get_db().execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        return error(exc.description, exc.code)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        clean, errors = validate_book(request.get_json(silent=True))
        if errors:
            return error("validation failed", 400, details=errors)
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (clean["title"], clean["author"], clean["year"], clean["isbn"]),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return error("a book with this isbn already exists", 409)
        response = jsonify(fetch_book(cur.lastrowid))
        response.status_code = 201
        response.headers["Location"] = f"/books/{cur.lastrowid}"
        return response

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        rows = get_db().execute(query + " ORDER BY id", params).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = fetch_book(book_id)
        if book is None:
            return error("book not found", 404)
        return jsonify(book)

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        if fetch_book(book_id) is None:
            return error("book not found", 404)
        clean, errors = validate_book(request.get_json(silent=True))
        if errors:
            return error("validation failed", 400, details=errors)
        db = get_db()
        try:
            db.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (clean["title"], clean["author"], clean["year"], clean["isbn"], book_id),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return error("a book with this isbn already exists", 409)
        return jsonify(fetch_book(book_id))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return error("book not found", 404)
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
