"""Book collection REST API built with Flask and SQLite."""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DATABASE = os.environ.get("BOOKS_DATABASE", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or DEFAULT_DATABASE

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.executescript(SCHEMA)
        db.close()

    def row_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_payload(data, partial=False):
        """Return (cleaned, errors). With partial=True only validate provided keys."""
        errors = []
        if not isinstance(data, dict):
            return None, ["Request body must be a JSON object."]
        cleaned = {}

        for field in ("title", "author"):
            if field in data or not partial:
                value = data.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"'{field}' is required and must be a non-empty string.")
                else:
                    cleaned[field] = value.strip()

        if "year" in data and data["year"] is not None:
            year = data["year"]
            if not isinstance(year, int) or isinstance(year, bool):
                errors.append("'year' must be an integer.")
            else:
                cleaned["year"] = year
        elif "year" in data:
            cleaned["year"] = None

        if "isbn" in data and data["isbn"] is not None:
            isbn = data["isbn"]
            if not isinstance(isbn, str):
                errors.append("'isbn' must be a string.")
            else:
                cleaned["isbn"] = isbn.strip()
        elif "isbn" in data:
            cleaned["isbn"] = None

        return cleaned, errors

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["Request body must be valid JSON."]}), 400
        cleaned, errors = validate_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (cleaned["title"], cleaned["author"], cleaned.get("year"), cleaned.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None:
            rows = db.execute("SELECT * FROM books WHERE author = ?", (author,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM books").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        return jsonify(row_to_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["Request body must be valid JSON."]}), 400
        cleaned, errors = validate_payload(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not cleaned:
            return jsonify({"errors": ["No updatable fields provided."]}), 400
        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        db.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*cleaned.values(), book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found."}), 404
        return "", 204

    @app.errorhandler(404)
    def not_found(exc):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(exc):
        return jsonify({"error": "Method not allowed."}), 405

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
