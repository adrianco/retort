"""Book collection REST API.

A small Flask service that manages a book collection backed by SQLite.

Endpoints:
    GET    /health         -> service health check
    POST   /books          -> create a book (title, author required; year, isbn optional)
    GET    /books          -> list all books (optional ?author= filter)
    GET    /books/<id>     -> fetch one book
    PUT    /books/<id>     -> update a book
    DELETE /books/<id>     -> delete a book

Run with:  python app.py   (listens on http://localhost:8000 by default)
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


def create_app(db_path: str = DEFAULT_DB_PATH) -> Flask:
    """Application factory.

    Args:
        db_path: Path to the SQLite database file. A relative path is
            resolved against the current working directory.
    """
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    @app.teardown_appcontext
    def close_db(_exc=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    def get_db() -> sqlite3.Connection:
        """Return a per-request SQLite connection (created on first use)."""
        if "db" not in g:
            conn = sqlite3.connect(app.config["DB_PATH"])
            conn.row_factory = sqlite3.Row
            g.db = conn
        return g.db

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def book_to_dict(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def parse_json_object() -> tuple[dict | None, str | None]:
        """Parse the request body as a JSON object.

        Returns (data, None) on success or (None, error_message) on failure.
        """
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return None, "Request body must be a valid JSON object"
        return data, None

    def validate_book(data: dict) -> tuple[dict, dict]:
        """Validate a book payload.

        title and author are required non-empty strings; year is an optional
        integer (numeric strings are accepted); isbn is an optional string.
        Returns (fields, errors); errors is empty when the payload is valid.
        """
        errors: dict[str, str] = {}

        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            errors["title"] = "title is required and must be a non-empty string"
        else:
            title = title.strip()

        author = data.get("author")
        if not isinstance(author, str) or not author.strip():
            errors["author"] = "author is required and must be a non-empty string"
        else:
            author = author.strip()

        year = data.get("year")
        if year is not None:
            if isinstance(year, bool) or not isinstance(year, (int, str)):
                errors["year"] = "year must be an integer"
            else:
                try:
                    year = int(year)
                except (TypeError, ValueError):
                    errors["year"] = "year must be an integer"
        else:
            year = None

        isbn = data.get("isbn")
        if isbn is None:
            isbn = None
        elif isinstance(isbn, str):
            isbn = isbn.strip() or None
        else:
            errors["isbn"] = "isbn must be a string"

        return (
            {"title": title, "author": author, "year": year, "isbn": isbn},
            errors,
        )

    # ------------------------------------------------------------------ #
    # Routes
    # ------------------------------------------------------------------ #

    @app.get("/")
    def index():
        return jsonify(
            {
                "service": "book-collection-api",
                "health": "/health",
                "books": "/books",
            }
        ), 200

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data, err = parse_json_object()
        if data is None:
            return jsonify({"error": err}), 400
        fields, errors = validate_book(data)
        if errors:
            return jsonify({"error": "Validation failed", "fields": errors}), 400
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (fields["title"], fields["author"], fields["year"], fields["isbn"]),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        conn = get_db()
        if author is not None:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data, err = parse_json_object()
        if data is None:
            return jsonify({"error": err}), 400
        fields, errors = validate_book(data)
        if errors:
            return jsonify({"error": "Validation failed", "fields": errors}), 400
        conn = get_db()
        cur = conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (fields["title"], fields["author"], fields["year"], fields["isbn"], book_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        conn = get_db()
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return jsonify({"message": f"Book {book_id} deleted"}), 200

    # ------------------------------------------------------------------ #
    # JSON error handlers (so every response is JSON)
    # ------------------------------------------------------------------ #

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(_e):
        return jsonify({"error": "Internal server error"}), 500

    # Create the schema up front.
    with app.app_context():
        conn = get_db()
        conn.executescript(SCHEMA)
        conn.commit()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
