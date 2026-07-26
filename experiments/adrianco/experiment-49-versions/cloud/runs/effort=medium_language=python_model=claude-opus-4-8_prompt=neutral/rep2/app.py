"""A small REST API for managing a book collection.

Framework: Flask. Storage: SQLite (via the stdlib sqlite3 module).
"""
import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db():
    """Return a request-scoped SQLite connection."""
    if "db" not in g:
        db_path = current_app_db_path()
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def current_app_db_path():
    from flask import current_app

    return current_app.config["DATABASE"]


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book(data, partial=False):
    """Validate an incoming book payload.

    Returns (cleaned_dict, errors_list). When partial=True only the fields
    that are present are validated (used for PUT), but required fields may
    not be set to empty.
    """
    errors = []
    cleaned = {}

    if not isinstance(data, dict):
        return None, ["Request body must be a JSON object"]

    # title and author are required (and must be non-empty strings).
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"'{field}' must be a non-empty string")
            else:
                cleaned[field] = value.strip()
        elif not partial:
            errors.append(f"'{field}' is required")

    if "year" in data and data["year"] is not None:
        value = data["year"]
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append("'year' must be an integer")
        else:
            cleaned["year"] = value
    elif "year" in data:
        cleaned["year"] = None

    if "isbn" in data:
        value = data["isbn"]
        if value is not None and not isinstance(value, str):
            errors.append("'isbn' must be a string")
        else:
            cleaned["isbn"] = value.strip() if isinstance(value, str) else None

    return cleaned, errors


def create_app(db_path=None, testing=False):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("BOOKS_DB", DEFAULT_DB)
    app.config["TESTING"] = testing

    init_db(app.config["DATABASE"])

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        cleaned, errors = validate_book(data if data is not None else None)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
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
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(row_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json(silent=True)
        cleaned, errors = validate_book(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not cleaned:
            return jsonify({"errors": ["No valid fields to update"]}), 400

        # Merge provided fields over the existing record.
        merged = row_to_dict(row)
        merged.update(cleaned)
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(row_to_dict(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
