"""Book collection REST API."""

from __future__ import annotations

import os
import sqlite3
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


def create_app(database_path: str | None = None) -> Flask:
    """Create and configure the application.

    Supplying ``database_path`` is useful for tests; production defaults to a
    ``books.db`` file alongside this module.
    """
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or os.environ.get(
        "BOOKS_DATABASE", os.path.join(app.root_path, "books.db")
    )

    with app.app_context():
        init_db()

    @app.get("/health")
    def health() -> tuple[Any, int]:
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book() -> tuple[Any, int]:
        data, error = validated_book_payload()
        if error:
            return jsonify({"error": error}), 400

        cursor = get_db().execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        get_db().commit()
        book = fetch_book(cursor.lastrowid)
        return jsonify(book), 201

    @app.get("/books")
    def list_books() -> tuple[Any, int]:
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        return jsonify([book_dict(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int) -> tuple[Any, int]:
        book = fetch_book(book_id)
        if book is None:
            return not_found()
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int) -> tuple[Any, int]:
        if fetch_book(book_id) is None:
            return not_found()
        data, error = validated_book_payload()
        if error:
            return jsonify({"error": error}), 400

        get_db().execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data.get("year"), data.get("isbn"), book_id),
        )
        get_db().commit()
        return jsonify(fetch_book(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int) -> tuple[Any, int]:
        cursor = get_db().execute("DELETE FROM books WHERE id = ?", (book_id,))
        get_db().commit()
        if cursor.rowcount == 0:
            return not_found()
        return "", 204

    @app.teardown_appcontext
    def close_db(_: BaseException | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db() -> None:
    get_db().executescript(SCHEMA)
    get_db().commit()


def book_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in ("id", "title", "author", "year", "isbn")}


def fetch_book(book_id: int) -> dict[str, Any] | None:
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return book_dict(row) if row else None


def validated_book_payload() -> tuple[dict[str, Any], str | None]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}, "Request body must be a JSON object."

    result: dict[str, Any] = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return {}, f"{field} is required and must be a non-empty string."
        result[field] = value.strip()

    year = data.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            return {}, "year must be an integer."
        result["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            return {}, "isbn must be a string."
        result["isbn"] = isbn.strip()
    return result, None


def not_found() -> tuple[Any, int]:
    return jsonify({"error": "Book not found."}), 404


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
