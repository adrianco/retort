"""A REST API service for managing a book collection.

Built with Flask and SQLite. The application factory ``create_app`` allows
tests to spin up isolated instances backed by their own database.
"""

import sqlite3
from flask import Flask, g, jsonify, request

DEFAULT_DB = "books.db"


def get_db(app):
    """Return a per-request SQLite connection, creating one if needed."""
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


def validate_book(data, partial=False):
    """Validate incoming book data.

    Returns a tuple ``(cleaned, errors)``. When ``partial`` is True (used for
    PUT), only the fields that are present are validated, but any present
    required field must still be non-empty.
    """
    errors = []
    cleaned = {}

    if not isinstance(data, dict):
        return None, ["Request body must be a JSON object"]

    # Required string fields: title, author
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"'{field}' must be a non-empty string")
            else:
                cleaned[field] = value.strip()
        elif not partial:
            errors.append(f"'{field}' is required")

    # Optional year field: must be an integer if provided
    if "year" in data and data["year"] is not None:
        value = data["year"]
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append("'year' must be an integer")
        else:
            cleaned["year"] = value
    elif "year" in data:
        cleaned["year"] = None

    # Optional isbn field: must be a string if provided
    if "isbn" in data and data["isbn"] is not None:
        value = data["isbn"]
        if not isinstance(value, str):
            errors.append("'isbn' must be a string")
        else:
            cleaned["isbn"] = value.strip()
    elif "isbn" in data:
        cleaned["isbn"] = None

    return cleaned, errors


def create_app(database=DEFAULT_DB):
    app = Flask(__name__)
    app.config["DATABASE"] = database

    init_db(app)

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        cleaned, errors = validate_book(data, partial=False)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

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
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
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

        cleaned, errors = validate_book(data, partial=True)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400
        if not cleaned:
            return jsonify({"error": "No valid fields to update"}), 400

        # Merge with existing values.
        updated = book_to_dict(row)
        updated.update(cleaned)

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                updated["title"],
                updated["author"],
                updated["year"],
                updated["isbn"],
                book_id,
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db(app)
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
