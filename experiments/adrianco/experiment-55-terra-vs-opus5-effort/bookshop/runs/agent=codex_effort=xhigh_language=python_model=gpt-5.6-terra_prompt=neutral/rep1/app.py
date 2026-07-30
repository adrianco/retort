"""Book collection REST API backed by SQLite.

Run this module directly for local development, or import ``create_app`` from
another WSGI server.  The database location can be set with the
``BOOKS_DATABASE`` environment variable.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g, jsonify, request


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
)
"""


def create_app(database_path: str | os.PathLike[str] | None = None) -> Flask:
    """Create and configure the Book Collection API application."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=str(
            database_path
            or os.environ.get("BOOKS_DATABASE")
            or Path(app.instance_path) / "books.sqlite3"
        )
    )

    # The default instance directory may not exist in a fresh checkout.
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_db(app)
    app.teardown_appcontext(close_db)

    @app.get("/health")
    def health() -> tuple[Any, int]:
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book() -> tuple[Any, int]:
        data, error = parse_book_payload()
        if error:
            return error_response(error, 400)

        cursor = get_db().execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        get_db().commit()
        book = fetch_book(cursor.lastrowid)
        return jsonify(book), 201

    @app.get("/books")
    def list_books() -> tuple[Any, int]:
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id"
            ).fetchall()
        else:
            rows = get_db().execute(
                """SELECT id, title, author, year, isbn FROM books
                   WHERE author = ? COLLATE NOCASE ORDER BY id""",
                (author,),
            ).fetchall()
        return jsonify([book_from_row(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int) -> tuple[Any, int]:
        book = fetch_book(book_id)
        if book is None:
            return error_response("book not found", 404)
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int) -> tuple[Any, int]:
        if fetch_book(book_id) is None:
            return error_response("book not found", 404)

        data, error = parse_book_payload()
        if error:
            return error_response(error, 400)

        get_db().execute(
            """UPDATE books SET title = ?, author = ?, year = ?, isbn = ?
               WHERE id = ?""",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        get_db().commit()
        return jsonify(fetch_book(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int) -> tuple[str, int]:
        cursor = get_db().execute("DELETE FROM books WHERE id = ?", (book_id,))
        get_db().commit()
        if cursor.rowcount == 0:
            return error_response("book not found", 404)
        return "", 204

    @app.errorhandler(404)
    def route_not_found(_error: Exception) -> tuple[Any, int]:
        return error_response("resource not found", 404)

    return app


def init_db(app: Flask) -> None:
    """Create the database schema if it is not already present."""
    database = Path(app.config["DATABASE"])
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    try:
        connection.execute(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def get_db() -> sqlite3.Connection:
    """Return one SQLite connection for the active Flask request."""
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def book_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def fetch_book(book_id: int) -> dict[str, Any] | None:
    row = get_db().execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return book_from_row(row) if row is not None else None


def parse_book_payload() -> tuple[dict[str, Any], str | None]:
    """Validate a create/update request and return normalized book fields."""
    if not request.is_json:
        return {}, "request body must be JSON"

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}, "request body must be a JSON object"

    title = data.get("title")
    author = data.get("author")
    if not isinstance(title, str) or not title.strip():
        return {}, "title is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return {}, "author is required and must be a non-empty string"

    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return {}, "year must be an integer or null"

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return {}, "isbn must be a string or null"

    return {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn.strip() if isinstance(isbn, str) else None,
    }, None


def error_response(message: str, status: int) -> tuple[Any, int]:
    return jsonify({"error": message}), status


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
