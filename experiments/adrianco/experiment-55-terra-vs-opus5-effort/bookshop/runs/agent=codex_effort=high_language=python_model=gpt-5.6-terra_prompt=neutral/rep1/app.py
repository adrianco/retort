"""Flask application providing a small SQLite-backed books API."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the books API application."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=str(Path(app.root_path) / "books.db"),
    )
    if test_config:
        app.config.update(test_config)

    @app.before_request
    def open_database() -> None:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        g.db = db

    @app.teardown_request
    def close_database(exception: BaseException | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify(error=error.name, message=error.description), error.code

    @app.errorhandler(sqlite3.Error)
    def handle_database_error(error: sqlite3.Error):
        current_app.logger.exception("Database error")
        return jsonify(error="Internal Server Error", message="Database operation failed"), 500

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.post("/books")
    def create_book():
        payload = get_json_payload()
        book = validate_book(payload, require_all=True)
        cursor = g.db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book["title"], book["author"], book.get("year"), book.get("isbn")),
        )
        g.db.commit()
        return jsonify(fetch_book(cursor.lastrowid)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is None:
            rows = g.db.execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = g.db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        return jsonify([book_to_dict(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        return jsonify(require_book(book_id)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        existing = require_book(book_id)
        payload = get_json_payload()
        # PUT accepts a complete representation or selected fields; after merging,
        # title and author must still be present and non-empty.
        merged = {key: existing[key] for key in ("title", "author", "year", "isbn")}
        merged.update(payload)
        book = validate_book(merged, require_all=True)
        g.db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book["title"], book["author"], book.get("year"), book.get("isbn"), book_id),
        )
        g.db.commit()
        return jsonify(fetch_book(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        require_book(book_id)
        g.db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        g.db.commit()
        return "", 204

    return app


def get_json_payload() -> dict[str, Any]:
    """Return the request's JSON object, or raise a JSON 400 response."""
    if not request.is_json:
        raise BadRequest("Request body must be a JSON object")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a JSON object")
    return payload


def validate_book(payload: dict[str, Any], require_all: bool) -> dict[str, Any]:
    """Validate and normalize fields accepted by the API."""
    allowed = {"title", "author", "year", "isbn"}
    unknown = set(payload) - allowed
    if unknown:
        raise BadRequest(f"Unknown field(s): {', '.join(sorted(unknown))}")

    normalized: dict[str, Any] = {}
    for field in ("title", "author"):
        value = payload.get(field)
        if require_all and (not isinstance(value, str) or not value.strip()):
            raise BadRequest(f"'{field}' is required and must be a non-empty string")
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise BadRequest(f"'{field}' must be a non-empty string")
            normalized[field] = value.strip()

    if "year" in payload:
        year = payload["year"]
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            raise BadRequest("'year' must be an integer or null")
        normalized["year"] = year

    if "isbn" in payload:
        isbn = payload["isbn"]
        if isbn is not None and not isinstance(isbn, str):
            raise BadRequest("'isbn' must be a string or null")
        normalized["isbn"] = isbn.strip() if isinstance(isbn, str) else isbn
    return normalized


def fetch_book(book_id: int) -> dict[str, Any]:
    row = g.db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise_not_found(book_id)
    return book_to_dict(row)


def require_book(book_id: int) -> dict[str, Any]:
    return fetch_book(book_id)


def raise_not_found(book_id: int) -> None:
    from flask import abort

    abort(404, description=f"Book {book_id} was not found")


def book_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "title": row["title"], "author": row["author"],
            "year": row["year"], "isbn": row["isbn"]}


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
