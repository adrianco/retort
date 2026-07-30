"""Book collection REST API backed by SQLite."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g, jsonify, request


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the application."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DATABASE", str(Path(app.instance_path) / "books.sqlite")),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close_database(_error: BaseException | None = None) -> None:
        database = g.pop("database", None)
        if database is not None:
            database.close()

    @app.get("/health")
    def health() -> tuple[Any, int]:
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book() -> tuple[Any, int]:
        payload, error = validated_book_payload()
        if error:
            return error

        cursor = get_database().execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload["title"], payload["author"], payload["year"], payload["isbn"]),
        )
        get_database().commit()
        return jsonify(fetch_book(cursor.lastrowid)), 201

    @app.get("/books")
    def list_books() -> tuple[Any, int]:
        author = request.args.get("author")
        database = get_database()
        if author is None:
            rows = database.execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = database.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        return jsonify([book_to_dict(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int) -> tuple[Any, int]:
        book = fetch_book(book_id)
        if book is None:
            return not_found(book_id)
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int) -> tuple[Any, int]:
        if fetch_book(book_id) is None:
            return not_found(book_id)
        payload, error = validated_book_payload()
        if error:
            return error
        database = get_database()
        database.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (payload["title"], payload["author"], payload["year"], payload["isbn"], book_id),
        )
        database.commit()
        return jsonify(fetch_book(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int) -> tuple[str, int]:
        database = get_database()
        deleted = database.execute("DELETE FROM books WHERE id = ?", (book_id,)).rowcount
        if not deleted:
            return not_found(book_id)
        database.commit()
        return "", 204

    with app.app_context():
        initialize_database()
    return app


def get_database() -> sqlite3.Connection:
    if "database" not in g:
        g.database = sqlite3.connect(current_app.config["DATABASE"])
        g.database.row_factory = sqlite3.Row
    return g.database


def initialize_database() -> None:
    get_database().execute(
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
    get_database().commit()


def validated_book_payload() -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, (jsonify({"error": "Request body must be a JSON object"}), 400)

    title = payload.get("title")
    author = payload.get("author")
    if not isinstance(title, str) or not title.strip():
        return None, (jsonify({"error": "title is required"}), 400)
    if not isinstance(author, str) or not author.strip():
        return None, (jsonify({"error": "author is required"}), 400)

    year = payload.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
        return None, (jsonify({"error": "year must be an integer"}), 400)
    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, (jsonify({"error": "isbn must be a string"}), 400)

    return {"title": title.strip(), "author": author.strip(), "year": year, "isbn": isbn}, None


def fetch_book(book_id: int) -> dict[str, Any] | None:
    row = get_database().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return book_to_dict(row) if row is not None else None


def book_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "title": row["title"], "author": row["author"], "year": row["year"], "isbn": row["isbn"]}


def not_found(book_id: int) -> tuple[Any, int]:
    return jsonify({"error": f"Book {book_id} not found"}), 404


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
