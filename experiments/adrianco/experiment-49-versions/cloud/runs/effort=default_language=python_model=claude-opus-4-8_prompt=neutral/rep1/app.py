"""A small REST API for managing a book collection.

Uses Flask for the HTTP layer and SQLite (via the stdlib ``sqlite3`` module)
for persistence. The application is created with an application factory so
that tests can spin up isolated instances backed by their own databases.
"""

import sqlite3

from flask import Flask, g, jsonify, request


def get_db(db_path):
    """Return a request-scoped SQLite connection, opening one if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(db_path):
    """Create the ``books`` table if it does not already exist."""
    conn = sqlite3.connect(db_path)
    try:
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
    finally:
        conn.close()


def book_to_dict(row):
    """Convert a ``sqlite3.Row`` into a plain, JSON-serialisable dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, partial=False):
    """Validate an incoming book payload.

    Returns a tuple ``(cleaned, error)``. Exactly one of the two is ``None``.
    When ``partial`` is True (used for PUT), only the fields that are present
    are validated, but any provided ``title``/``author`` must be non-empty.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    cleaned = {}

    # title / author: required (unless partial) and must be non-empty strings.
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                return None, f"'{field}' must be a non-empty string"
            cleaned[field] = value.strip()
        elif not partial:
            return None, f"'{field}' is required"

    # year: optional, but if present must be an integer.
    if "year" in data and data["year"] is not None:
        value = data["year"]
        if isinstance(value, bool) or not isinstance(value, int):
            return None, "'year' must be an integer"
        cleaned["year"] = value
    elif "year" in data:
        cleaned["year"] = None

    # isbn: optional string.
    if "isbn" in data and data["isbn"] is not None:
        value = data["isbn"]
        if not isinstance(value, str):
            return None, "'isbn' must be a string"
        cleaned["isbn"] = value.strip()
    elif "isbn" in data:
        cleaned["isbn"] = None

    return cleaned, None


def create_app(db_path="books.db"):
    """Application factory. ``db_path`` selects the SQLite database file."""
    app = Flask(__name__)
    init_db(db_path)

    @app.teardown_appcontext
    def close_db(exception):  # noqa: ARG001 - Flask passes the exception
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        cleaned, error = validate_book_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db(db_path)
        cursor = db.execute(
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
            "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        db = get_db(db_path)
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db(db_path)
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        cleaned, error = validate_book_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400
        if not cleaned:
            return jsonify({"error": "No fields provided to update"}), 400

        db = get_db(db_path)
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {assignments} WHERE id = ?", values)
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db(db_path)
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
