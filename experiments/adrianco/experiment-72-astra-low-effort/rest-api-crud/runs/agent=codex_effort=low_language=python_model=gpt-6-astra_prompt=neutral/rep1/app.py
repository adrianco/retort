"""Flask REST API backed by a persistent SQLite book collection."""

import os
import sqlite3

from flask import Flask, g, jsonify, request, url_for
from werkzeug.exceptions import HTTPException

SQLITE_INTEGER_MIN = -(2**63)
SQLITE_INTEGER_MAX = 2**63 - 1


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(DATABASE=os.environ.get("BOOKS_DATABASE", "books.sqlite3"))
    if config:
        app.config.update(config)

    def database():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_database(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        with database() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )
            """)

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    def validated_book():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Body must be a JSON object")
        for field in ("title", "author"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise ValueError(f"{field} is required and must be a non-empty string")
        if data.get("year") is not None and type(data["year"]) is not int:
            raise ValueError("year must be an integer or null")
        if data.get("year") is not None and not (
            SQLITE_INTEGER_MIN <= data["year"] <= SQLITE_INTEGER_MAX
        ):
            raise ValueError("year must fit in a signed 64-bit integer")
        if data.get("isbn") is not None and not isinstance(data["isbn"], str):
            raise ValueError("isbn must be a string or null")
        return (data["title"].strip(), data["author"].strip(),
                data.get("year"), data.get("isbn"))

    @app.errorhandler(ValueError)
    def validation_error(error):
        return jsonify(error=str(error)), 400

    def find_book(book_id):
        if book_id > SQLITE_INTEGER_MAX:
            return None
        return database().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    @app.get("/health")
    def health():
        database().execute("SELECT 1")
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        values = validated_book()
        with database() as db:
            cursor = db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", values)
            book_id = cursor.lastrowid
        response = jsonify(dict(find_book(book_id)))
        response.status_code = 201
        response.headers["Location"] = url_for("get_book", book_id=book_id)
        return response

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is None:
            rows = database().execute("SELECT * FROM books ORDER BY id")
        else:
            rows = database().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,))
        return jsonify([dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = find_book(book_id)
        if book is None:
            return jsonify(error="Book not found"), 404
        return jsonify(dict(book))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        values = validated_book()
        if book_id > SQLITE_INTEGER_MAX:
            return jsonify(error="Book not found"), 404
        with database() as db:
            cursor = db.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (*values, book_id))
        if not cursor.rowcount:
            return jsonify(error="Book not found"), 404
        return jsonify(dict(find_book(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        if book_id > SQLITE_INTEGER_MAX:
            return jsonify(error="Book not found"), 404
        with database() as db:
            cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if not cursor.rowcount:
            return jsonify(error="Book not found"), 404
        return jsonify(deleted=book_id)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
