"""A small REST API for managing a book collection.

Built with Flask and SQLite. Use ``create_app()`` to construct an
application instance; pass a custom ``db_path`` (e.g. ``":memory:"``)
for testing.
"""

import sqlite3

from flask import Flask, jsonify, request

DEFAULT_DB_PATH = "books.db"


def create_app(db_path=DEFAULT_DB_PATH):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    def get_db():
        """Return the shared SQLite connection, creating it on demand.

        A single connection is held for the lifetime of the app so that an
        in-memory database (``:memory:``) survives across requests. SQLite
        serialises writes internally, and ``check_same_thread=False`` lets
        the dev server's worker threads share the connection.
        """
        if getattr(app, "_db", None) is None:
            conn = sqlite3.connect(
                app.config["DB_PATH"], check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            app._db = conn
        return app._db

    def init_db():
        get_db().executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            );
            """
        )
        get_db().commit()

    def book_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_payload(data, partial=False):
        """Validate a book payload.

        Returns ``(cleaned, error)``. ``error`` is ``None`` on success.
        When ``partial`` is True (PUT), only supplied fields are checked,
        but any supplied ``title``/``author`` must still be non-empty.
        """
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object"

        cleaned = {}

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
            if not isinstance(value, int) or isinstance(value, bool):
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

    @app.route("/health", methods=["GET"])
    def health():
        try:
            get_db().execute("SELECT 1")
            return jsonify({"status": "ok"}), 200
        except sqlite3.Error:
            return jsonify({"status": "error"}), 500

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        cleaned, error = validate_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
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
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json(silent=True)
        cleaned, error = validate_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400
        if not cleaned:
            return jsonify({"error": "No valid fields to update"}), 400

        columns = ", ".join(f"{field} = ?" for field in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {columns} WHERE id = ?", values)
        db.commit()

        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    app.init_db = init_db
    init_db()
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
