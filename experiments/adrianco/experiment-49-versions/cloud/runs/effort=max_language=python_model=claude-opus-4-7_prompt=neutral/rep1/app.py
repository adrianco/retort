from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import Flask, g, jsonify, request

DEFAULT_DB = "books.db"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(g.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exception: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_schema(database_path: str) -> None:
    conn = sqlite3.connect(database_path)
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


def row_to_book(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "request body must be a JSON object"

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return None, "title is required and must be a non-empty string"

    author = payload.get("author")
    if not isinstance(author, str) or not author.strip():
        return None, "author is required and must be a non-empty string"

    year = payload.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return None, "year must be an integer if provided"

    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "isbn must be a string if provided"

    isbn_clean: str | None = isbn.strip() if isinstance(isbn, str) else None
    if isbn_clean == "":
        isbn_clean = None

    return (
        {
            "title": title.strip(),
            "author": author.strip(),
            "year": year,
            "isbn": isbn_clean,
        },
        None,
    )


def create_app(database: str | None = None) -> Flask:
    app = Flask(__name__)
    database_path = database or os.environ.get("BOOKS_DB", DEFAULT_DB)
    init_schema(database_path)

    @app.before_request
    def _attach_db_path() -> None:
        g.database_path = database_path

    app.teardown_appcontext(close_db)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data, err = validate_book_payload(request.get_json(silent=True))
        if err:
            return jsonify({"error": err}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        db.commit()
        book_id = cur.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row)), 201, {"Location": f"/books/{book_id}"}

    @app.get("/books")
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author is not None:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        db = get_db()
        existing = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "book not found"}), 404
        data, err = validate_book_payload(request.get_json(silent=True))
        if err:
            return jsonify({"error": err}), 400
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        db.commit()
        updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        db = get_db()
        existing = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    @app.errorhandler(404)
    def _not_found(_err):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def _method_not_allowed(_err):
        return jsonify({"error": "method not allowed"}), 405

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
