"""Book collection REST API backed by SQLite."""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from typing import Any

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def _row_to_book(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _get_db() -> sqlite3.Connection:
    conn = getattr(g, "_db", None)
    if conn is None:
        conn = sqlite3.connect(g.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g._db = conn
    return conn


def _init_db(db_path: str) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
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


def _validate_payload(payload: Any, *, partial: bool = False) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"

    allowed = {"title", "author", "year", "isbn"}
    unknown = set(payload) - allowed
    if unknown:
        return None, f"Unknown field(s): {', '.join(sorted(unknown))}"

    cleaned: dict[str, Any] = {}

    if not partial or "title" in payload:
        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            return None, "'title' is required and must be a non-empty string"
        cleaned["title"] = title.strip()

    if not partial or "author" in payload:
        author = payload.get("author")
        if not isinstance(author, str) or not author.strip():
            return None, "'author' is required and must be a non-empty string"
        cleaned["author"] = author.strip()

    if "year" in payload:
        year = payload["year"]
        if year is not None and not isinstance(year, int):
            return None, "'year' must be an integer or null"
        cleaned["year"] = year

    if "isbn" in payload:
        isbn = payload["isbn"]
        if isbn is not None and not isinstance(isbn, str):
            return None, "'isbn' must be a string or null"
        cleaned["isbn"] = isbn.strip() if isinstance(isbn, str) else isbn

    return cleaned, None


def create_app(db_path: str = DEFAULT_DB_PATH) -> Flask:
    app = Flask(__name__)
    _init_db(db_path)

    @app.before_request
    def _attach_db_path() -> None:
        g.db_path = db_path

    @app.teardown_appcontext
    def _close_db(_exc: BaseException | None) -> None:
        conn = getattr(g, "_db", None)
        if conn is not None:
            conn.close()

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book() -> Any:
        payload = request.get_json(silent=True)
        cleaned, err = _validate_payload(payload, partial=False)
        if err:
            return jsonify({"error": err}), 400

        db = _get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned.get("year"),
                cleaned.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(_row_to_book(row)), 201

    @app.get("/books")
    def list_books() -> Any:
        db = _get_db()
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int) -> Any:
        db = _get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(_row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int) -> Any:
        db = _get_db()
        existing = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404

        payload = request.get_json(silent=True)
        cleaned, err = _validate_payload(payload, partial=True)
        if err:
            return jsonify({"error": err}), 400
        if not cleaned:
            return jsonify({"error": "No fields to update"}), 400

        columns = ", ".join(f"{k} = ?" for k in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {columns} WHERE id = ?", values)
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_row_to_book(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int) -> Any:
        db = _get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
