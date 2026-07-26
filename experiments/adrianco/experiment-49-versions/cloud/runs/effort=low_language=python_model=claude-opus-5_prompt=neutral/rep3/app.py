"""Book collection REST API (Flask + SQLite)."""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", DEFAULT_DB)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)

    def row_to_book(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate(payload, partial=False):
        """Return (cleaned, errors)."""
        errors = []
        if not isinstance(payload, dict):
            return None, ["request body must be a JSON object"]

        cleaned = {}
        for field in ("title", "author"):
            if field in payload:
                value = payload[field]
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{field} must be a non-empty string")
                else:
                    cleaned[field] = value.strip()
            elif not partial:
                errors.append(f"{field} is required")

        if payload.get("year") is not None:
            year = payload["year"]
            if isinstance(year, bool) or not isinstance(year, int):
                errors.append("year must be an integer")
            else:
                cleaned["year"] = year
        else:
            cleaned["year"] = None

        if payload.get("isbn") is not None:
            isbn = payload["isbn"]
            if not isinstance(isbn, str):
                errors.append("isbn must be a string")
            else:
                cleaned["isbn"] = isbn.strip()
        else:
            cleaned["isbn"] = None

        return cleaned, errors

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1")
        return jsonify(status="ok"), 200

    @app.post("/books")
    def create_book():
        cleaned, errors = validate(request.get_json(silent=True))
        if errors:
            return jsonify(errors=errors), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"]),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_book(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify(error="book not found"), 404
        return jsonify(row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        if db.execute("SELECT 1 FROM books WHERE id = ?", (book_id,)).fetchone() is None:
            return jsonify(error="book not found"), 404
        cleaned, errors = validate(request.get_json(silent=True))
        if errors:
            return jsonify(errors=errors), 400
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"], book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify(error="book not found"), 404
        return "", 204

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def not_allowed(_e):
        return jsonify(error="method not allowed"), 405

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
