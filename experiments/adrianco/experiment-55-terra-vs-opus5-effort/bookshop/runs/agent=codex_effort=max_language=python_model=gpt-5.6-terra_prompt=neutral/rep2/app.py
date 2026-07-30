"""Book collection REST API backed by SQLite."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, Response, g, jsonify, request


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


class PayloadValidationError(ValueError):
    """Raised when a request body cannot represent a valid book."""


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the application.

    ``DATABASE`` can be overridden by tests or set with the BOOKS_DATABASE
    environment variable when running the service.
    """

    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "BOOKS_DATABASE", str(Path(app.root_path) / "books.sqlite3")
        ),
        TESTING=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    with app.app_context():
        init_db()

    @app.get("/health")
    def health() -> Response:
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book() -> tuple[Response, int]:
        try:
            payload = validate_book_payload()
        except PayloadValidationError as error:
            return jsonify({"error": str(error)}), 400

        connection = get_db()
        cursor = connection.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload["title"], payload["author"], payload["year"], payload["isbn"]),
        )
        connection.commit()
        book = get_book(cursor.lastrowid)
        return jsonify(book), 201

    @app.get("/books")
    def list_books() -> Response:
        author = request.args.get("author")
        connection = get_db()

        if author is None:
            rows = connection.execute(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id"
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, title, author, year, isbn
                FROM books
                WHERE author = ? COLLATE NOCASE
                ORDER BY id
                """,
                (author,),
            ).fetchall()

        return jsonify([book_from_row(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def read_book(book_id: int) -> tuple[Response, int] | Response:
        book = get_book(book_id)
        if book is None:
            return not_found_response()
        return jsonify(book)

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int) -> tuple[Response, int] | Response:
        try:
            payload = validate_book_payload()
        except PayloadValidationError as error:
            return jsonify({"error": str(error)}), 400

        connection = get_db()
        cursor = connection.execute(
            """
            UPDATE books
            SET title = ?, author = ?, year = ?, isbn = ?
            WHERE id = ?
            """,
            (
                payload["title"],
                payload["author"],
                payload["year"],
                payload["isbn"],
                book_id,
            ),
        )
        connection.commit()

        if cursor.rowcount == 0:
            return not_found_response()

        return jsonify(get_book(book_id))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int) -> tuple[Response, int] | Response:
        connection = get_db()
        cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
        connection.commit()

        if cursor.rowcount == 0:
            return not_found_response()

        return "", 204

    @app.errorhandler(404)
    def route_not_found(_: Any) -> tuple[Response, int]:
        return not_found_response()

    @app.errorhandler(405)
    def method_not_allowed(_: Any) -> tuple[Response, int]:
        return jsonify({"error": "Method not allowed"}), 405

    @app.teardown_appcontext
    def close_db(_: Any = None) -> None:
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    return app


def get_db() -> sqlite3.Connection:
    """Return the current request's SQLite connection."""

    if "db" not in g:
        connection = sqlite3.connect(current_database_path())
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def current_database_path() -> str:
    """Get the configured database path without importing Flask globals eagerly."""

    from flask import current_app

    return str(current_app.config["DATABASE"])


def init_db() -> None:
    """Create the books table if it does not already exist."""

    get_db().executescript(SCHEMA)
    get_db().commit()


def get_book(book_id: int | None) -> dict[str, Any] | None:
    if book_id is None:
        return None
    row = get_db().execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return book_from_row(row) if row is not None else None


def book_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload() -> dict[str, str | int | None]:
    """Validate a complete book payload used by POST and PUT requests."""

    if not request.is_json:
        raise PayloadValidationError("Request body must be JSON")

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise PayloadValidationError("Request body must be a JSON object")

    title = required_text(payload, "title")
    author = required_text(payload, "author")
    year = optional_year(payload)
    isbn = optional_text(payload, "isbn")
    return {"title": title, "author": author, "year": year, "isbn": isbn}


def required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PayloadValidationError(f"{field} is required and must be a non-empty string")
    return value.strip()


def optional_text(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise PayloadValidationError(f"{field} must be a string or null")
    return value.strip()


def optional_year(payload: dict[str, Any]) -> int | None:
    value = payload.get("year")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PayloadValidationError("year must be an integer or null")
    if not 0 <= value <= 9999:
        raise PayloadValidationError("year must be between 0 and 9999")
    return value


def not_found_response() -> tuple[Response, int]:
    return jsonify({"error": "Book not found"}), 404


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
