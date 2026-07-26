"""Book collection REST API built with Flask and SQLite.

Run directly (``python app.py``) or via the Flask CLI (``flask --app app run``);
the Flask CLI discovers the ``create_app`` factory automatically.
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException

DEFAULT_DB_PATH = "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


def get_db():
    """Return a SQLite connection scoped to the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


def validate_book(data):
    """Validate a POST/PUT payload.

    Returns ``(book, errors)`` where exactly one is None. ``book`` holds the
    cleaned values for all four columns; unknown fields are ignored.
    """
    if not isinstance(data, dict):
        return None, {"body": "Request body must be a JSON object."}

    errors = {}

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors["title"] = "Required and must be a non-empty string."

    author = data.get("author")
    if not isinstance(author, str) or not author.strip():
        errors["author"] = "Required and must be a non-empty string."

    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "Must be an integer."

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "Must be a string."

    if errors:
        return None, errors

    return (
        {
            "title": title.strip(),
            "author": author.strip(),
            "year": year,
            "isbn": (isbn.strip() or None) if isinstance(isbn, str) else None,
        },
        None,
    )


def validation_error(errors):
    return jsonify({"error": "Validation failed.", "details": errors}), 400


def book_not_found(book_id):
    return jsonify({"error": f"Book {book_id} not found."}), 404


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    init_db(app.config["DATABASE"])
    app.teardown_appcontext(close_db)

    def fetch_book(book_id):
        row = get_db().execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        return None if row is None else dict(row)

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1")
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        book, errors = validate_book(request.get_json(silent=True))
        if errors:
            return validation_error(errors)
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book["title"], book["author"], book["year"], book["isbn"]),
        )
        db.commit()
        created = fetch_book(cur.lastrowid)
        return jsonify(created), 201, {"Location": f"/books/{created['id']}"}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        rows = get_db().execute(query + " ORDER BY id", params).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = fetch_book(book_id)
        if book is None:
            return book_not_found(book_id)
        return jsonify(book)

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        if fetch_book(book_id) is None:
            return book_not_found(book_id)
        book, errors = validate_book(request.get_json(silent=True))
        if errors:
            return validation_error(errors)
        db = get_db()
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book["title"], book["author"], book["year"], book["isbn"], book_id),
        )
        db.commit()
        return jsonify(fetch_book(book_id))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return book_not_found(book_id)
        return "", 204

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        return jsonify({"error": exc.description}), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        return jsonify({"error": "Internal server error."}), 500

    return app


if __name__ == "__main__":
    create_app().run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
