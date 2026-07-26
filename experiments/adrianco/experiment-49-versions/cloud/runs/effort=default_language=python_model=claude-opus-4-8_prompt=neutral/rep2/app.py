"""A REST API service for managing a book collection.

Built with Flask and SQLite (via the stdlib ``sqlite3`` module).
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db(app):
    """Return a request-scoped SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(app):
    """Create the books table if it does not already exist."""
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


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, partial=False):
    """Validate an incoming book payload.

    Returns a tuple ``(cleaned, errors)``. When ``partial`` is True (used for
    PUT), only the fields that are present are validated, but title/author may
    not be blanked out.
    """
    errors = []
    if not isinstance(data, dict):
        return None, ["Request body must be a JSON object"]

    cleaned = {}

    def check_required_str(field):
        value = data.get(field)
        if value is None or not isinstance(value, str) or not value.strip():
            errors.append(f"'{field}' is required and must be a non-empty string")
        else:
            cleaned[field] = value.strip()

    if partial:
        # For updates, only validate the fields that were supplied.
        for field in ("title", "author"):
            if field in data:
                check_required_str(field)
    else:
        check_required_str("title")
        check_required_str("author")

    # Optional fields.
    if "year" in data and data["year"] is not None:
        year = data["year"]
        if isinstance(year, bool) or not isinstance(year, int):
            errors.append("'year' must be an integer")
        else:
            cleaned["year"] = year
    elif "year" in data:
        cleaned["year"] = None

    if "isbn" in data and data["isbn"] is not None:
        isbn = data["isbn"]
        if not isinstance(isbn, str):
            errors.append("'isbn' must be a string")
        else:
            cleaned["isbn"] = isbn.strip()
    elif "isbn" in data:
        cleaned["isbn"] = None

    return cleaned, errors


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    init_db(app)

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        cleaned, errors = validate_book_payload(data, partial=False)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db(app)
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

    @app.route("/books", methods=["GET"])
    def list_books():
        db = get_db(app)
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = get_db(app)
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        db = get_db(app)
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json(silent=True)
        cleaned, errors = validate_book_payload(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not cleaned:
            return jsonify({"error": "No valid fields provided to update"}), 400

        # Merge supplied fields onto the existing record.
        merged = book_to_dict(row)
        merged.update(cleaned)
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db(app)
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
