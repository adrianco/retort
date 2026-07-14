"""A REST API for managing a book collection.

Built with Flask and SQLite (Python's built-in embedded database).
"""
import os
import sqlite3

from flask import Flask, g, jsonify, request

DATABASE = os.environ.get("BOOKS_DB", os.path.join(os.path.dirname(__file__), "books.db"))


def get_db():
    """Return a per-request SQLite connection, creating one if needed."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(db=None):
    """Create the books table if it does not already exist."""
    close_after = False
    if db is None:
        db = sqlite3.connect(DATABASE)
        close_after = True
    db.execute(
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
    db.commit()
    if close_after:
        db.close()


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book(data, partial=False):
    """Validate incoming book payload.

    Returns (cleaned_dict, error_message). error_message is None when valid.
    When partial=True (PUT), only validates fields that are present.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    cleaned = {}

    # title and author are required (unless partial update without them)
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                return None, f"'{field}' must be a non-empty string"
            cleaned[field] = value.strip()
        elif not partial:
            return None, f"'{field}' is required"

    if "year" in data and data["year"] is not None:
        value = data["year"]
        if isinstance(value, bool) or not isinstance(value, int):
            return None, "'year' must be an integer"
        cleaned["year"] = value
    elif "year" in data:
        cleaned["year"] = None

    if "isbn" in data:
        value = data["isbn"]
        if value is not None and not isinstance(value, str):
            return None, "'isbn' must be a string"
        cleaned["isbn"] = value.strip() if isinstance(value, str) else None

    return cleaned, None


def create_app():
    app = Flask(__name__)

    with app.app_context():
        init_db()

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        cleaned, error = validate_book(request.get_json(silent=True))
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (cleaned["title"], cleaned["author"], cleaned.get("year"), cleaned.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        cleaned, error = validate_book(request.get_json(silent=True), partial=True)
        if error:
            return jsonify({"error": error}), 400
        if not cleaned:
            return jsonify({"error": "No valid fields to update"}), 400

        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {assignments} WHERE id = ?", values)
        db.commit()
        updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
