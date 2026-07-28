"""Flask REST API for a small SQLite-backed book collection."""

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, request


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
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DATABASE", str(Path(__file__).with_name("books.db")))
    )
    if test_config:
        app.config.update(test_config)

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    def initialize_db() -> None:
        database = get_db()
        database.execute(SCHEMA)
        database.commit()

    @app.before_request
    def ensure_database() -> None:
        initialize_db()

    @app.teardown_appcontext
    def close_db(exception: BaseException | None = None) -> None:
        database = g.pop("db", None)
        if database is not None:
            database.close()

    def error(message: str, status: int):
        return jsonify(error=message), status

    def book_json(row: sqlite3.Row) -> dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def request_data() -> dict[str, Any] | None:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None
        return data

    def validate_fields(data: dict[str, Any], *, partial: bool = False) -> str | None:
        if not partial or "title" in data:
            if not isinstance(data.get("title"), str) or not data["title"].strip():
                return "title is required and must be a non-empty string"
        if not partial or "author" in data:
            if not isinstance(data.get("author"), str) or not data["author"].strip():
                return "author is required and must be a non-empty string"
        if "year" in data and data["year"] is not None and (
            isinstance(data["year"], bool) or not isinstance(data["year"], int)
        ):
            return "year must be an integer or null"
        if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
            return "isbn must be a string or null"
        return None

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        data = request_data()
        if data is None:
            return error("request body must be a JSON object", 400)
        problem = validate_fields(data)
        if problem:
            return error(problem, 400)
        database = get_db()
        cursor = database.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn")),
        )
        database.commit()
        row = database.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(book_json(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        database = get_db()
        if author is None:
            rows = database.execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = database.execute(
                "SELECT * FROM books WHERE author LIKE ? ORDER BY id", (f"%{author}%",)
            ).fetchall()
        return jsonify([book_json(row) for row in rows])

    def find_book(book_id: int):
        return get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        row = find_book(book_id)
        return jsonify(book_json(row)) if row else error("book not found", 404)

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        if not find_book(book_id):
            return error("book not found", 404)
        data = request_data()
        if data is None:
            return error("request body must be a JSON object", 400)
        problem = validate_fields(data, partial=True)
        if problem:
            return error(problem, 400)
        allowed = {"title", "author", "year", "isbn"}
        unknown = set(data) - allowed
        if unknown:
            return error(f"unknown field: {next(iter(unknown))}", 400)
        current = find_book(book_id)
        values = {key: data.get(key, current[key]) for key in allowed}
        values["title"] = values["title"].strip()
        values["author"] = values["author"].strip()
        database = get_db()
        database.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (values["title"], values["author"], values["year"], values["isbn"], book_id),
        )
        database.commit()
        return jsonify(book_json(find_book(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        if not find_book(book_id):
            return error("book not found", 404)
        database = get_db()
        database.execute("DELETE FROM books WHERE id = ?", (book_id,))
        database.commit()
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
