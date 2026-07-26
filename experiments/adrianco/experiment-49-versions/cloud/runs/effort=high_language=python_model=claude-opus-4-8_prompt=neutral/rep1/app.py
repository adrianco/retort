"""A small REST API for managing a book collection.

Built with Flask and backed by SQLite (via the standard-library ``sqlite3``
module). Data is stored on disk so the collection survives restarts.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

from flask import Flask, g, jsonify, request

# The database file can be overridden via an environment variable, which keeps
# tests isolated from a developer's real data.
DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    """Create the ``books`` table if it does not yet exist."""
    conn = _connect(db_path)
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


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


class ValidationError(Exception):
    """Raised when incoming book data fails validation."""


def _validate_book(payload: Optional[dict]) -> dict:
    """Validate and normalise a book payload for create/update.

    ``title`` and ``author`` are required and must be non-blank. ``year`` must
    be an integer when supplied and ``isbn`` a string when supplied.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")

    title = payload.get("title")
    author = payload.get("author")

    if not isinstance(title, str) or not title.strip():
        raise ValidationError("'title' is required and must be a non-empty string")
    if not isinstance(author, str) or not author.strip():
        raise ValidationError("'author' is required and must be a non-empty string")

    year = payload.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        raise ValidationError("'year' must be an integer")

    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        raise ValidationError("'isbn' must be a string")

    return {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn,
    }


def create_app(db_path: Optional[str] = None) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH

    init_db(app.config["DB_PATH"])

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = _connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exception: Optional[BaseException]) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        return jsonify({"error": str(err)}), 400

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = _validate_book(request.get_json(silent=True))
        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(_row_to_book(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_book(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(_row_to_book(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id: int):
        data = _validate_book(request.get_json(silent=True))
        db = get_db()
        existing = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_row_to_book(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id: int):
        db = get_db()
        existing = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return jsonify({"detail": "Book deleted"}), 200

    return app


# Module-level app for `flask run` / WSGI servers.
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
