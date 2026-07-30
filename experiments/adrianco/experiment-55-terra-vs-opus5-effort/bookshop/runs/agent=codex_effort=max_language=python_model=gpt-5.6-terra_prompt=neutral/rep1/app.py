"""Flask REST API for a small SQLite-backed book collection."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import HTTPException


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
)
"""


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the book collection application."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "BOOKS_DATABASE", str(Path(app.root_path) / "books.sqlite3")
        )
    )

    if test_config:
        app.config.update(test_config)

    @app.before_request
    def ensure_database() -> None:
        init_db()

    @app.teardown_appcontext
    def close_db(_error: BaseException | None = None) -> None:
        # An in-memory database is intentionally kept alive for the lifetime of
        # its application, so separate requests can share its contents.
        if current_app.config["DATABASE"] != ":memory:":
            db = g.pop("db", None)
            if db is not None:
                db.close()

    @app.errorhandler(HTTPException)
    def json_http_error(error: HTTPException):
        return jsonify(error=error.name.lower().replace(" ", "_"), message=error.description), error.code

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        payload, error = validated_book_payload()
        if error is not None:
            return error

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload["title"], payload["author"], payload["year"], payload["isbn"]),
        )
        db.commit()
        book = find_book(cursor.lastrowid)
        return jsonify(book_to_dict(book)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is None:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        return jsonify([book_to_dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        book = find_book(book_id)
        if book is None:
            return not_found()
        return jsonify(book_to_dict(book))

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        if find_book(book_id) is None:
            return not_found()

        payload, error = validated_book_payload()
        if error is not None:
            return error

        db = get_db()
        db.execute(
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
        db.commit()
        return jsonify(book_to_dict(find_book(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return not_found()
        return "", 204

    return app


def get_db() -> sqlite3.Connection:
    """Return the SQLite connection associated with the active request."""
    database = current_app.config["DATABASE"]

    if database == ":memory:":
        db = current_app.extensions.get("book_collection_memory_db")
        if db is None:
            db = sqlite3.connect(database, check_same_thread=False)
            db.row_factory = sqlite3.Row
            current_app.extensions["book_collection_memory_db"] = db
        return db

    if "db" not in g:
        database_path = Path(database)
        if database_path.parent != Path("."):
            database_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(database)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db() -> None:
    """Create the books table if it has not already been created."""
    db = get_db()
    db.execute(SCHEMA)
    db.commit()


def find_book(book_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


def book_to_dict(book: sqlite3.Row) -> dict[str, Any]:
    return dict(book)


def validated_book_payload() -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    """Parse and validate a full book representation from the request body."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, validation_error({"body": "A JSON object is required."})

    errors: dict[str, str] = {}
    title = data.get("title")
    author = data.get("author")

    if not isinstance(title, str) or not title.strip():
        errors["title"] = "Title is required and must be a non-empty string."
    if not isinstance(author, str) or not author.strip():
        errors["author"] = "Author is required and must be a non-empty string."

    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "Year must be an integer or null."

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "ISBN must be a string or null."

    if errors:
        return None, validation_error(errors)

    return {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn.strip() if isinstance(isbn, str) else isbn,
    }, None


def validation_error(details: dict[str, str]) -> tuple[Any, int]:
    return jsonify(error="validation_error", details=details), 400


def not_found() -> tuple[Any, int]:
    return jsonify(error="not_found", message="Book not found."), 404


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
