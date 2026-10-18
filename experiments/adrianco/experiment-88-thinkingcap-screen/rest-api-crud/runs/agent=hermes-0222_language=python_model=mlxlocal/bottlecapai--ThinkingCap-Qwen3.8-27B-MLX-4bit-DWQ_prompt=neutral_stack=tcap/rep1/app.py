"""Book Collection REST API.

A small Flask + SQLite service for managing a book collection.

Endpoints:
    GET    /health          - health check
    POST   /books           - create a book (title, author required)
    GET    /books           - list books (optional ?author= filter)
    GET    /books/<id>      - get a single book
    PUT    /books/<id>      - update a book (partial updates allowed)
    DELETE /books/<id>      - delete a book
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")


def get_db() -> sqlite3.Connection:
    """Return the per-request SQLite connection (created on first use)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path: str) -> None:
    """Create the books table if it does not exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
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
        conn.commit()
    finally:
        conn.close()


def row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def parse_book_payload(data: dict, partial: bool = False) -> tuple[dict, str | None]:
    """Validate a create/update payload.

    Returns (clean_fields, error_message). error_message is None when valid.
    title and author are required (non-empty strings); year must be an int;
    isbn must be a string. In partial mode missing keys are simply skipped.
    """
    fields: dict = {}

    for key in ("title", "author"):
        if key not in data:
            if not partial:
                return {}, f"'{key}' is required"
            continue
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            return {}, f"'{key}' must be a non-empty string"
        fields[key] = value.strip()

    if "year" in data and data["year"] is not None:
        value = data["year"]
        if isinstance(value, bool) or not isinstance(value, int):
            return {}, "'year' must be an integer"
        fields["year"] = value

    if "isbn" in data and data["isbn"] is not None:
        value = data["isbn"]
        if not isinstance(value, str) or not value.strip():
            return {}, "'isbn' must be a non-empty string"
        fields["isbn"] = value.strip()

    return fields, None


def create_app(db_path: str = DEFAULT_DB_PATH) -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = db_path
    app.teardown_appcontext(close_db)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400

        fields, error = parse_book_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (fields["title"], fields["author"], fields.get("year"), fields.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(row_to_book(row)), 201

    @app.get("/books")
    def list_books():
        query = "SELECT * FROM books"
        params: list = []
        author = request.args.get("author")
        if author is not None and author != "":
            query += " WHERE author = ?"
            params.append(author)
        query += " ORDER BY id"

        rows = get_db().execute(query, params).fetchall()
        return jsonify([row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400

        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404

        fields, error = parse_book_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400

        if not fields:
            return jsonify({"error": "no valid fields to update"}), 400

        for key, value in fields.items():
            db.execute(f"UPDATE books SET {key} = ? WHERE id = ?", (value, book_id))
        db.commit()

        updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    init_db(app.config["DATABASE"])
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
