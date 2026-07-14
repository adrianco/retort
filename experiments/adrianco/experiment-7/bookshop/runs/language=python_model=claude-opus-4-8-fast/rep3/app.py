"""A small REST API for managing a book collection.

Built with Flask and the standard-library sqlite3 module.
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db():
    """Return a request-scoped SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db(db_path):
    """Create the books table if it does not already exist."""
    conn = sqlite3.connect(db_path)
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


def create_app(db_path=None):
    """Application factory so tests can use an isolated database."""
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    init_db(app.config["DATABASE"])

    @app.teardown_appcontext
    def close_db(exception):  # noqa: ARG001
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def validate_book_payload(data, partial=False):
        """Return (cleaned_dict, error_message)."""
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object."

        cleaned = {}

        # title and author are required (unless partial update).
        for field in ("title", "author"):
            if field in data:
                value = data[field]
                if not isinstance(value, str) or not value.strip():
                    return None, f"'{field}' must be a non-empty string."
                cleaned[field] = value.strip()
            elif not partial:
                return None, f"'{field}' is required."

        if "year" in data and data["year"] is not None:
            try:
                cleaned["year"] = int(data["year"])
            except (TypeError, ValueError):
                return None, "'year' must be an integer."

        if "isbn" in data and data["isbn"] is not None:
            if not isinstance(data["isbn"], str):
                return None, "'isbn' must be a string."
            cleaned["isbn"] = data["isbn"].strip()

        return cleaned, None

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        cleaned, error = validate_book_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
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
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404

        data = request.get_json(silent=True)
        cleaned, error = validate_book_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned.get("year"),
                cleaned.get("isbn"),
                book_id,
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


# Module-level app for `flask run` / gunicorn.
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
