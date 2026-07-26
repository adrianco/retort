"""A small REST API for managing a book collection.

Built with Flask and the standard-library ``sqlite3`` module. The application
is exposed through a factory (:func:`create_app`) so it can be instantiated
against an in-memory database for tests or a file-backed database in
production.
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db(app):
    """Return a per-request SQLite connection, creating it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(app):
    """Create the ``books`` table if it does not already exist."""
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate_book(data, partial=False):
    """Validate an incoming book payload.

    Returns a tuple ``(cleaned, error)``. When ``partial`` is True (used by
    PUT), only the fields that are present are validated, but any field that
    *is* present must still be valid.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    cleaned = {}

    # title / author are required (unless partial and omitted).
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                return None, f"'{field}' must be a non-empty string"
            cleaned[field] = value.strip()
        elif not partial:
            return None, f"'{field}' is required"

    # year is optional but must be an integer when supplied.
    if "year" in data and data["year"] is not None:
        year = data["year"]
        if isinstance(year, bool) or not isinstance(year, int):
            return None, "'year' must be an integer"
        cleaned["year"] = year
    elif "year" in data:
        cleaned["year"] = None

    # isbn is optional but must be a string when supplied.
    if "isbn" in data and data["isbn"] is not None:
        isbn = data["isbn"]
        if not isinstance(isbn, str):
            return None, "'isbn' must be a string"
        cleaned["isbn"] = isbn.strip()
    elif "isbn" in data:
        cleaned["isbn"] = None

    return cleaned, None


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or DEFAULT_DB_PATH

    init_db(app)

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        cleaned, error = _validate_book(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db(app)
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned.get("year"),
                cleaned.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(_book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db(app)
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db(app)
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(_book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        db = get_db(app)
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        cleaned, error = _validate_book(data, partial=True)
        if error:
            return jsonify({"error": error}), 400
        if not cleaned:
            return jsonify({"error": "No valid fields to update"}), 400

        merged = _book_to_dict(row)
        merged.update(cleaned)
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                merged["title"],
                merged["author"],
                merged["year"],
                merged["isbn"],
                book_id,
            ),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(_book_to_dict(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db(app)
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
