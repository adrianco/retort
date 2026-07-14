"""A small REST API for managing a book collection.

Built with Flask and SQLite. Use ``create_app`` to construct an application
instance (the database path can be overridden, which keeps the tests isolated).
"""

from __future__ import annotations

import sqlite3
from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = "books.db"


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_app(db_path: str = DEFAULT_DB_PATH) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            conn = sqlite3.connect(app.config["DB_PATH"])
            conn.row_factory = sqlite3.Row
            g.db = conn
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):  # noqa: ARG001 - signature required by Flask
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db() -> None:
        db = get_db()
        db.execute(
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
        db.commit()

    with app.app_context():
        init_db()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        title = data.get("title")
        author = data.get("author")
        errors = []
        if not isinstance(title, str) or not title.strip():
            errors.append("title is required")
        if not isinstance(author, str) or not author.strip():
            errors.append("author is required")

        year = data.get("year")
        if year is not None and not isinstance(year, int):
            errors.append("year must be an integer")

        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            errors.append("isbn must be a string")

        if errors:
            return jsonify({"error": "; ".join(errors)}), 400

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title.strip(), author.strip(), year, isbn),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(_row_to_book(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_book(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id: int):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(_row_to_book(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id: int):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        # Allow partial updates: fall back to existing values when a field is
        # omitted, but validate any field that is provided.
        title = data.get("title", row["title"])
        author = data.get("author", row["author"])
        year = data.get("year", row["year"])
        isbn = data.get("isbn", row["isbn"])

        errors = []
        if not isinstance(title, str) or not title.strip():
            errors.append("title is required")
        if not isinstance(author, str) or not author.strip():
            errors.append("author is required")
        if year is not None and not isinstance(year, int):
            errors.append("year must be an integer")
        if isbn is not None and not isinstance(isbn, str):
            errors.append("isbn must be a string")
        if errors:
            return jsonify({"error": "; ".join(errors)}), 400

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title.strip(), author.strip(), year, isbn, book_id),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(_row_to_book(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id: int):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
