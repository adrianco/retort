"""REST API for a small SQLite-backed book collection."""

from __future__ import annotations

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
        DATABASE=os.environ.get("DATABASE", str(Path(app.instance_path) / "books.db")),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        connection.execute(SCHEMA)

    @app.teardown_appcontext
    def close_db(_error: BaseException | None = None) -> None:
        database = g.pop("database", None)
        if database is not None:
            database.close()

    def get_db() -> sqlite3.Connection:
        if "database" not in g:
            g.database = sqlite3.connect(app.config["DATABASE"])
            g.database.row_factory = sqlite3.Row
        return g.database

    def book_json(row: sqlite3.Row) -> dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def payload() -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return None, (jsonify(error="Request body must be a JSON object"), 400)
        return body, None

    def validate_book(data: dict[str, Any], partial: bool = False) -> str | None:
        for field in ("title", "author"):
            if not partial or field in data:
                value = data.get(field)
                if not isinstance(value, str) or not value.strip():
                    return f"{field} is required"
        if "year" in data and data["year"] is not None:
            if isinstance(data["year"], bool) or not isinstance(data["year"], int):
                return "year must be an integer or null"
        if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
            return "isbn must be a string or null"
        unknown = set(data) - {"title", "author", "year", "isbn"}
        if unknown:
            return f"unknown field: {sorted(unknown)[0]}"
        return None

    @app.get("/health")
    def health() -> Any:
        return jsonify(status="ok")

    @app.post("/books")
    def create_book() -> Any:
        data, error = payload()
        if error:
            return error
        validation_error = validate_book(data)  # type: ignore[arg-type]
        if validation_error:
            return jsonify(error=validation_error), 400
        database = get_db()
        cursor = database.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn")),  # type: ignore[index]
        )
        database.commit()
        row = database.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(book_json(row)), 201

    @app.get("/books")
    def list_books() -> Any:
        author = request.args.get("author")
        database = get_db()
        if author is None:
            rows = database.execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = database.execute(
                "SELECT * FROM books WHERE author LIKE ? COLLATE NOCASE ORDER BY id",
                (f"%{author}%",),
            ).fetchall()
        return jsonify([book_json(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int) -> Any:
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify(error="Book not found"), 404
        return jsonify(book_json(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int) -> Any:
        data, error = payload()
        if error:
            return error
        database = get_db()
        existing = database.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify(error="Book not found"), 404
        validation_error = validate_book(data, partial=True)  # type: ignore[arg-type]
        if validation_error:
            return jsonify(error=validation_error), 400
        values = {key: data.get(key, existing[key]) for key in ("title", "author", "year", "isbn")}
        database.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (values["title"].strip(), values["author"].strip(), values["year"], values["isbn"], book_id),  # type: ignore[union-attr]
        )
        database.commit()
        row = database.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_json(row))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int) -> Any:
        database = get_db()
        cursor = database.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            return jsonify(error="Book not found"), 404
        database.commit()
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
