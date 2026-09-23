"""A small SQLite-backed REST API for a book collection."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, jsonify, request


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = str(
        database_path or os.environ.get("BOOKS_DATABASE", Path(__file__).with_name("books.db"))
    )

    def connect():
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def db_session():
        connection = connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with db_session() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )"""
        )

    def as_book(row):
        return dict(row)

    def book_payload(require_all=False):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, (jsonify(error="Request body must be a JSON object"), 400)
        allowed = {"title", "author", "year", "isbn"}
        unknown = set(data) - allowed
        if unknown:
            return None, (jsonify(error="Unknown field(s): " + ", ".join(sorted(unknown))), 400)
        if require_all and not {"title", "author"}.issubset(data):
            return None, (jsonify(error="title and author are required"), 400)
        if not require_all and not data:
            return None, (jsonify(error="At least one field is required"), 400)
        for field in ("title", "author"):
            if field in data and (not isinstance(data[field], str) or not data[field].strip()):
                return None, (jsonify(error=f"{field} must be a non-empty string"), 400)
        if "year" in data and data["year"] is not None and (
            isinstance(data["year"], bool) or not isinstance(data["year"], int)
        ):
            return None, (jsonify(error="year must be an integer or null"), 400)
        if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
            return None, (jsonify(error="isbn must be a string or null"), 400)
        return {key: (value.strip() if key in ("title", "author") else value)
                for key, value in data.items()}, None

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.post("/books")
    def create_book():
        data, error = book_payload(require_all=True)
        if error:
            return error
        with db_session() as db:
            cursor = db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn")),
            )
            book = as_book(db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone())
        return jsonify(book), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        with db_session() as db:
            if author is None:
                rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
        return jsonify([as_book(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        with db_session() as db:
            row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify(error="Book not found"), 404
        return jsonify(as_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data, error = book_payload(require_all=True)
        if error:
            return error
        with db_session() as db:
            exists = db.execute("SELECT 1 FROM books WHERE id = ?", (book_id,)).fetchone()
            if exists is None:
                return jsonify(error="Book not found"), 404
            db.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data["title"], data["author"], data.get("year"), data.get("isbn"), book_id),
            )
            row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(as_book(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        with db_session() as db:
            cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            return jsonify(error="Book not found"), 404
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run()
