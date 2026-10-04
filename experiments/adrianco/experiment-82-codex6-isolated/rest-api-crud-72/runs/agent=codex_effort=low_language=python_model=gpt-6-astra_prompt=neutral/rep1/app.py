"""Flask REST API backed by SQLite."""

import os
import sqlite3
from pathlib import Path

from flask import Flask, current_app, g, jsonify, request, url_for
from werkzeug.exceptions import BadRequest, HTTPException


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def validate_book():
    if not request.is_json:
        raise BadRequest("Request body must be JSON.")
    data = request.get_json()
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object.")
    unknown = data.keys() - {"title", "author", "year", "isbn"}
    if unknown:
        raise BadRequest("Unknown fields: " + ", ".join(sorted(unknown)))
    result = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BadRequest(f"{field} must be a non-empty string.")
        result[field] = value.strip()
    year = data.get("year")
    if year is not None and (type(year) is not int or not 1 <= year <= 9999):
        raise BadRequest("year must be an integer between 1 and 9999 or null.")
    isbn = data.get("isbn")
    if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
        raise BadRequest("isbn must be a non-empty string or null.")
    result.update(year=year, isbn=isbn.strip() if isbn is not None else None)
    return result


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get(
        "BOOKS_DATABASE", str(Path(__file__).with_name("books.sqlite3"))
    )
    if config:
        app.config.update(config)

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        with get_db() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )"""
            )

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({"error": error.description})
        response.content_type = "application/json"
        return response

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        app.logger.error("Database operation failed", exc_info=error)
        return jsonify(error="Database unavailable."), 503

    def find_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            from werkzeug.exceptions import NotFound

            raise NotFound("Book not found.")
        return dict(row)

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        book = validate_book()
        with get_db() as db:
            cursor = db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            book_id = cursor.lastrowid
        return jsonify(find_book(book_id)), 201, {"Location": url_for("get_book", book_id=book_id)}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        return jsonify(find_book(book_id))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        book = validate_book()
        with get_db() as db:
            cursor = db.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            if not cursor.rowcount:
                return jsonify(error="Book not found."), 404
        return jsonify(find_book(book_id))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        with get_db() as db:
            cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if not cursor.rowcount:
                return jsonify(error="Book not found."), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
