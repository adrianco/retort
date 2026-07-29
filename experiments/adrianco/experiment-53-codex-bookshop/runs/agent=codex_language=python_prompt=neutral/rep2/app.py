"""A small REST API for a SQLite-backed book collection."""

import os
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, request


DEFAULT_DATABASE = Path(__file__).with_name("books.db")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("DATABASE_PATH", str(DEFAULT_DATABASE)),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data, error = _json_body()
        if error:
            return error
        error = _validate_book(data)
        if error:
            return error

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn")),
        )
        db.commit()
        book = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(_book_dict(book)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id", (author,)
            ).fetchall()
        return jsonify([_book_dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = _find_book(book_id)
        if book is None:
            return _not_found()
        return jsonify(_book_dict(book))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        if _find_book(book_id) is None:
            return _not_found()
        data, error = _json_body()
        if error:
            return error
        error = _validate_book(data)
        if error:
            return error
        db = get_db()
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn"), book_id),
        )
        db.commit()
        return jsonify(_book_dict(_find_book(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        if _find_book(book_id) is None:
            return _not_found()
        db = get_db()
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    @app.teardown_appcontext
    def close_db(_exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    return app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app_database())
        g.db.row_factory = sqlite3.Row
    return g.db


def current_app_database():
    from flask import current_app

    return current_app.config["DATABASE"]


def init_db():
    db = get_db()
    db.execute(
        """CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )"""
    )
    db.commit()


def _find_book(book_id):
    return get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


def _book_dict(book):
    return {key: book[key] for key in ("id", "title", "author", "year", "isbn")}


def _json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "Request body must be a JSON object"}), 400)
    return data, None


def _validate_book(data):
    missing = [field for field in ("title", "author") if field not in data]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400
    if not isinstance(data["title"], str) or not data["title"].strip():
        return jsonify({"error": "title must be a non-empty string"}), 400
    if not isinstance(data["author"], str) or not data["author"].strip():
        return jsonify({"error": "author must be a non-empty string"}), 400
    if "year" in data and data["year"] is not None and (
        isinstance(data["year"], bool) or not isinstance(data["year"], int)
    ):
        return jsonify({"error": "year must be an integer or null"}), 400
    if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
        return jsonify({"error": "isbn must be a string or null"}), 400
    return None


def _not_found():
    return jsonify({"error": "Book not found"}), 404


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
