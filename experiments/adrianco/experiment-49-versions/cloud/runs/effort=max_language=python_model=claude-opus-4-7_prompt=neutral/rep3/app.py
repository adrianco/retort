"""Flask REST API for managing a book collection."""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

ALLOWED_FIELDS = {"title", "author", "year", "isbn"}
REQUIRED_FIELDS = ("title", "author")


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT    NOT NULL,
            author TEXT    NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )
        """
    )
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate_new_book(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"

    unknown = set(payload) - ALLOWED_FIELDS
    if unknown:
        return None, f"Unknown field(s): {', '.join(sorted(unknown))}"

    cleaned: dict[str, Any] = {}
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            return None, f"'{field}' is required and must be a non-empty string"
        cleaned[field] = value.strip()

    year = payload.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            return None, "'year' must be an integer"
        cleaned["year"] = year
    else:
        cleaned["year"] = None

    isbn = payload.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str) or not isbn.strip():
            return None, "'isbn' must be a non-empty string if provided"
        cleaned["isbn"] = isbn.strip()
    else:
        cleaned["isbn"] = None

    return cleaned, None


def _validate_update(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"
    if not payload:
        return None, "Request body must contain at least one field to update"

    unknown = set(payload) - ALLOWED_FIELDS
    if unknown:
        return None, f"Unknown field(s): {', '.join(sorted(unknown))}"

    cleaned: dict[str, Any] = {}
    for field in ("title", "author"):
        if field in payload:
            value = payload[field]
            if not isinstance(value, str) or not value.strip():
                return None, f"'{field}' must be a non-empty string"
            cleaned[field] = value.strip()

    if "year" in payload:
        year = payload["year"]
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            return None, "'year' must be an integer or null"
        cleaned["year"] = year

    if "isbn" in payload:
        isbn = payload["isbn"]
        if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
            return None, "'isbn' must be a non-empty string or null"
        cleaned["isbn"] = isbn.strip() if isinstance(isbn, str) else isbn

    return cleaned, None


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH

    with _connect(app.config["DB_PATH"]) as conn:
        _init_schema(conn)

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = _connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc: BaseException | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(_err):
        return jsonify({"error": "Internal server error"}), 500

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        payload = request.get_json(silent=True)
        cleaned, err = _validate_new_book(payload)
        if err:
            return jsonify({"error": err}), 400

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"]),
        )
        db.commit()
        book_id = cursor.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        return jsonify(_row_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        payload = request.get_json(silent=True)
        cleaned, err = _validate_update(payload)
        if err:
            return jsonify({"error": err}), 400

        db = get_db()
        existing = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404

        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {assignments} WHERE id = ?", values)
        db.commit()

        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_row_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
