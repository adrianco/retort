"""REST API for managing a SQLite-backed book collection."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, Response, current_app, g, jsonify, request, url_for


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    author TEXT NOT NULL CHECK (length(trim(author)) > 0),
    year INTEGER,
    isbn TEXT
);
"""


def create_app(database_path: str | os.PathLike[str] | None = None) -> Flask:
    """Create and configure the application.

    ``database_path`` is exposed primarily to make isolated test databases easy
    to create.  In normal use, set ``BOOKS_DATABASE`` or use ``books.db`` in
    the current directory.
    """
    app = Flask(__name__)
    app.config["DATABASE"] = str(
        database_path
        or os.environ.get("BOOKS_DATABASE")
        or Path.cwd() / "books.db"
    )

    @app.teardown_appcontext
    def close_db(_: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        init_db()

    @app.get("/health")
    def health() -> Response:
        return jsonify(status="ok")

    @app.post("/books")
    def create_book() -> tuple[Response, int]:
        payload, error = json_payload()
        if error:
            return error_response(error, 400)

        values, error = validate_book_fields(payload, require_title_and_author=True)
        if error:
            return error_response(error, 400)

        cursor = get_db().execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (values["title"], values["author"], values.get("year"), values.get("isbn")),
        )
        get_db().commit()
        book = get_book_or_none(cursor.lastrowid)
        response = jsonify(book)
        response.headers["Location"] = url_for("get_book", book_id=cursor.lastrowid)
        return response, 201

    @app.get("/books")
    def list_books() -> Response:
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        return jsonify([book_from_row(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int) -> Response:
        book = get_book_or_none(book_id)
        if book is None:
            return error_response("Book not found", 404)
        return jsonify(book)

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int) -> Response:
        existing = get_book_or_none(book_id)
        if existing is None:
            return error_response("Book not found", 404)

        payload, error = json_payload()
        if error:
            return error_response(error, 400)

        values, error = validate_book_fields(payload, require_title_and_author=False)
        if error:
            return error_response(error, 400)

        # Allow clients to update one or more fields while preserving the
        # required title and author from the existing record.
        updated = {**existing, **values}
        if not updated["title"] or not updated["author"]:
            return error_response("title and author are required", 400)

        get_db().execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                updated["title"],
                updated["author"],
                updated.get("year"),
                updated.get("isbn"),
                book_id,
            ),
        )
        get_db().commit()
        return jsonify(get_book_or_none(book_id))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int) -> tuple[Response, int] | Response:
        if get_book_or_none(book_id) is None:
            return error_response("Book not found", 404)
        get_db().execute("DELETE FROM books WHERE id = ?", (book_id,))
        get_db().commit()
        return "", 204

    return app


def get_db() -> sqlite3.Connection:
    """Return the request-local SQLite connection."""
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        g.db = db
    return g.db


def init_db() -> None:
    """Create the books table if it does not already exist."""
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def get_book_or_none(book_id: int) -> dict[str, Any] | None:
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return book_from_row(row) if row is not None else None


def book_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "title": row["title"], "author": row["author"], "year": row["year"], "isbn": row["isbn"]}


def json_payload() -> tuple[dict[str, Any] | None, str | None]:
    """Read a JSON object, returning an API-friendly validation error."""
    if not request.is_json:
        return None, "Request body must be a JSON object"
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"
    return payload, None


def validate_book_fields(
    payload: dict[str, Any], *, require_title_and_author: bool
) -> tuple[dict[str, Any], str | None]:
    """Validate supplied book fields and return a clean value dictionary."""
    allowed = {"title", "author", "year", "isbn"}
    unexpected = set(payload) - allowed
    if unexpected:
        return {}, f"Unknown field: {sorted(unexpected)[0]}"

    if require_title_and_author and ("title" not in payload or "author" not in payload):
        return {}, "title and author are required"

    values: dict[str, Any] = {}
    for name in ("title", "author"):
        if name in payload:
            value = payload[name]
            if not isinstance(value, str) or not value.strip():
                return {}, f"{name} is required and must be a non-empty string"
            values[name] = value.strip()

    if "year" in payload:
        year = payload["year"]
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            return {}, "year must be an integer or null"
        values["year"] = year

    if "isbn" in payload:
        isbn = payload["isbn"]
        if isbn is not None and not isinstance(isbn, str):
            return {}, "isbn must be a string or null"
        values["isbn"] = isbn.strip() if isinstance(isbn, str) else isbn

    return values, None


def error_response(message: str, status_code: int) -> tuple[Response, int]:
    return jsonify(error=message), status_code


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
