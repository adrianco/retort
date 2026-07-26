"""REST API for managing a book collection.

Run with:  python app.py           (development server on :8000)
       or:  flask --app app run
"""

import os
import sqlite3

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from db import close_db, get_db, init_db, row_to_book
from validation import ValidationError, validate_book

DEFAULT_DATABASE = os.environ.get("BOOKS_DB_PATH", "books.db")


def error_response(status, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or DEFAULT_DATABASE
    app.teardown_appcontext(close_db)
    init_db(app)

    # ---------------------------------------------------------------- helpers

    def parse_json_body():
        """Return the parsed JSON body or raise ValidationError."""
        if not request.is_json:
            raise ValidationError({"body": "Content-Type must be application/json"})
        try:
            payload = request.get_json()
        except HTTPException:
            raise ValidationError({"body": "request body is not valid JSON"})
        if payload is None:
            raise ValidationError({"body": "request body is required"})
        return payload

    def fetch_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return row_to_book(row) if row else None

    # ----------------------------------------------------------------- routes

    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
        except sqlite3.Error as exc:
            return jsonify({"status": "error", "database": str(exc)}), 503
        return jsonify({"status": "ok", "database": "ok"}), 200

    @app.post("/books")
    def create_book():
        book = validate_book(parse_json_body())
        db = get_db()
        try:
            cursor = db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return error_response(409, f"A book with ISBN {book['isbn']} already exists")

        created = fetch_book(cursor.lastrowid)
        return jsonify(created), 201, {"Location": f"/books/{created['id']}"}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is not None and author.strip():
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author.strip(),),
            )
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id")
        return jsonify([row_to_book(row) for row in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = fetch_book(book_id)
        if book is None:
            return error_response(404, f"Book {book_id} not found")
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        book = validate_book(parse_json_body())
        db = get_db()
        try:
            cursor = db.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?,"
                " updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return error_response(409, f"A book with ISBN {book['isbn']} already exists")

        if cursor.rowcount == 0:
            return error_response(404, f"Book {book_id} not found")
        return jsonify(fetch_book(book_id)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return error_response(404, f"Book {book_id} not found")
        return "", 204

    # ------------------------------------------------------------ error handling

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc):
        return error_response(400, "Validation failed", exc.errors)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        return error_response(exc.code, exc.description)

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):  # pragma: no cover - safety net
        app.logger.exception("Unhandled error", exc_info=exc)
        return error_response(500, "Internal server error")

    return app


# `flask --app app run` discovers create_app() automatically; importing this
# module has no side effects so the test suite can pick its own database.
if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 8000)))
