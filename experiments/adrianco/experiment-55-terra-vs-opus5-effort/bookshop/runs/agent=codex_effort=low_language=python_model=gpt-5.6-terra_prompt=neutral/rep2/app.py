"""A small Flask REST API for a SQLite-backed book collection."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, current_app, g, jsonify, request


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DATABASE", str(Path(app.root_path) / "books.db")),
    )
    if test_config:
        app.config.update(test_config)

    with app.app_context():
        init_db()

    @app.teardown_appcontext
    def close_db(_: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        data, error = validated_payload()
        if error:
            return error
        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        db.commit()
        return jsonify(book_by_id(cursor.lastrowid)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        return jsonify([serialize_book(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        book = book_by_id(book_id)
        return (jsonify(book), 200) if book else not_found()

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        if book_by_id(book_id) is None:
            return not_found()
        data, error = validated_payload()
        if error:
            return error
        db = get_db()
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        db.commit()
        return jsonify(book_by_id(book_id))

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
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db() -> None:
    get_db().execute(
        """CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )"""
    )
    get_db().commit()


def serialize_book(row: sqlite3.Row) -> dict:
    return dict(row)


def book_by_id(book_id: int) -> dict | None:
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return serialize_book(row) if row else None


def validated_payload() -> tuple[dict | None, tuple[object, int] | None]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(error="Request body must be a JSON object"), 400)

    title = data.get("title")
    author = data.get("author")
    if not isinstance(title, str) or not title.strip():
        return None, (jsonify(error="title is required"), 400)
    if not isinstance(author, str) or not author.strip():
        return None, (jsonify(error="author is required"), 400)

    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return None, (jsonify(error="year must be an integer"), 400)
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, (jsonify(error="isbn must be a string"), 400)
    return {"title": title.strip(), "author": author.strip(), "year": year, "isbn": isbn}, None


def not_found():
    return jsonify(error="Book not found"), 404


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
