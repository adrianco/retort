"""REST API for managing a book collection.

A small Flask application backed by SQLite. Provides CRUD operations on
books plus a health check endpoint.
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

# Database path can be overridden (used by the test suite for isolation).
DATABASE = os.environ.get("BOOKS_DB", os.path.join(os.path.dirname(__file__), "books.db"))


def get_db():
    """Return a SQLite connection scoped to the current app context."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def init_db(db=None):
    """Create the books table if it does not already exist."""
    close_after = False
    if db is None:
        db = sqlite3.connect(DATABASE)
        close_after = True
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT NOT NULL,
            author  TEXT NOT NULL,
            year    INTEGER,
            isbn    TEXT
        )
        """
    )
    db.commit()
    if close_after:
        db.close()


def book_to_dict(row):
    """Convert a sqlite3.Row into a plain dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_payload(data, partial=False):
    """Validate a book payload.

    Returns (cleaned_dict, error_message). error_message is None when valid.
    When ``partial`` is True (PUT), only the fields that are present are
    validated, but at least one updatable field must be supplied.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    cleaned = {}

    # title and author are required (on create); when present they must be
    # non-empty strings.
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                return None, f"'{field}' must be a non-empty string"
            cleaned[field] = value.strip()
        elif not partial:
            return None, f"'{field}' is required"

    if "year" in data and data["year"] is not None:
        try:
            cleaned["year"] = int(data["year"])
        except (TypeError, ValueError):
            return None, "'year' must be an integer"
    elif "year" in data:
        cleaned["year"] = None

    if "isbn" in data:
        isbn = data["isbn"]
        if isbn is not None and not isinstance(isbn, str):
            return None, "'isbn' must be a string"
        cleaned["isbn"] = isbn

    if partial and not cleaned:
        return None, "No updatable fields supplied"

    return cleaned, None


def create_app():
    app = Flask(__name__)

    with app.app_context():
        init_db(get_db())

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        cleaned, error = validate_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        cursor = db.execute(
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
            "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        cleaned, error = validate_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {assignments} WHERE id = ?", values)
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
