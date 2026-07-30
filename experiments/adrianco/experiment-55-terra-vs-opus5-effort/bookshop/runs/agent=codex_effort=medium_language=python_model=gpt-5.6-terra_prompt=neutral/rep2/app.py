"""Book collection REST API."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g, jsonify, request


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DATABASE", str(Path(app.instance_path) / "books.sqlite")),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        init_db()

    @app.teardown_appcontext
    def close_db(_: BaseException | None = None) -> None:
        database = g.pop("db", None)
        if database is not None:
            database.close()

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.post("/books")
    def create_book():
        payload, error = json_payload()
        if error:
            return error
        normalized, error = validate_book(payload)
        if error:
            return error

        cursor = get_db().execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (normalized["title"], normalized["author"], normalized["year"], normalized["isbn"]),
        )
        get_db().commit()
        return jsonify(book_by_id(cursor.lastrowid)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id", (author,)
            ).fetchall()
        return jsonify([book_dict(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        book = book_by_id(book_id)
        if book is None:
            return not_found(book_id)
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        existing = book_by_id(book_id)
        if existing is None:
            return not_found(book_id)
        payload, error = json_payload()
        if error:
            return error
        normalized, error = validate_book(payload, existing)
        if error:
            return error

        get_db().execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (normalized["title"], normalized["author"], normalized["year"], normalized["isbn"], book_id),
        )
        get_db().commit()
        return jsonify(book_by_id(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        cursor = get_db().execute("DELETE FROM books WHERE id = ?", (book_id,))
        get_db().commit()
        if cursor.rowcount == 0:
            return not_found(book_id)
        return "", 204

    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db() -> None:
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        """
    )
    get_db().commit()


def book_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "title": row["title"], "author": row["author"], "year": row["year"], "isbn": row["isbn"]}


def book_by_id(book_id: int) -> dict[str, Any] | None:
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return book_dict(row) if row else None


def json_payload() -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    if not request.is_json:
        return None, (jsonify(error="Request body must be JSON"), 415)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, (jsonify(error="JSON body must be an object"), 400)
    return payload, None


def validate_book(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    """Validate a create payload or merge a PUT payload with an existing book."""
    allowed = {"title", "author", "year", "isbn"}
    unknown = set(payload) - allowed
    if unknown:
        return None, (jsonify(error=f"Unknown field: {sorted(unknown)[0]}"), 400)

    values = {key: payload.get(key, existing.get(key) if existing else None) for key in allowed}
    for field in ("title", "author"):
        if not isinstance(values[field], str) or not values[field].strip():
            return None, (jsonify(error=f"{field} is required and must be a non-empty string"), 400)
        values[field] = values[field].strip()
    if values["year"] is not None and (isinstance(values["year"], bool) or not isinstance(values["year"], int)):
        return None, (jsonify(error="year must be an integer or null"), 400)
    if values["isbn"] is not None and not isinstance(values["isbn"], str):
        return None, (jsonify(error="isbn must be a string or null"), 400)
    return values, None


def not_found(book_id: int):
    return jsonify(error=f"Book {book_id} was not found"), 404


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
