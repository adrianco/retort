"""Book collection REST API.

A small Flask service for managing a collection of books, backed by SQLite.

Run with:
    python app.py

The app factory ``create_app`` makes it easy to point the service at a
different database file (used by the test-suite to isolate state).
"""

from __future__ import annotations

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")

# Fields that may be supplied by clients. Anything else in the payload is
# ignored so callers cannot inject arbitrary columns.
ALLOWED_FIELDS = ("title", "author", "year", "isbn")


def create_app(db_path: str = DEFAULT_DB) -> Flask:
    """Build and configure the Flask application.

    Args:
        db_path: Path to the SQLite database file. Use ``":memory:"`` only
            with care -- a fresh connection per request would lose the data,
            so tests use a temporary file instead.
    """
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    def get_db() -> sqlite3.Connection:
        """Return a per-request SQLite connection, creating it on first use."""
        if "db" not in g:
            conn = sqlite3.connect(app.config["DB_PATH"])
            conn.row_factory = sqlite3.Row
            g.db = conn
        return g.db

    @app.teardown_appcontext
    def close_db(_exc: BaseException | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db() -> None:
        db = get_db()
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

    # Initialise the schema once at startup, within an app context.
    with app.app_context():
        init_db()

    # ----- helpers ---------------------------------------------------------

    def row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_payload(data: object, *, partial: bool) -> tuple[dict, list[str]]:
        """Validate and normalise an incoming JSON payload.

        Args:
            data: The parsed JSON body.
            partial: When True (PUT), missing fields are allowed; when False
                (POST), ``title`` and ``author`` are required.

        Returns:
            A tuple of (cleaned_fields, errors). ``cleaned_fields`` only
            contains keys that were supplied and valid.
        """
        errors: list[str] = []
        if not isinstance(data, dict):
            return {}, ["request body must be a JSON object"]

        cleaned: dict = {}

        # title / author: required (on create) and must be non-empty strings.
        for field in ("title", "author"):
            if field in data:
                value = data[field]
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{field} must be a non-empty string")
                else:
                    cleaned[field] = value.strip()
            elif not partial:
                errors.append(f"{field} is required")

        # year: optional, must be an integer if present.
        if "year" in data and data["year"] is not None:
            value = data["year"]
            # Guard against bool (a subclass of int) sneaking through.
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append("year must be an integer")
            else:
                cleaned["year"] = value
        elif "year" in data:
            cleaned["year"] = None

        # isbn: optional, must be a string if present.
        if "isbn" in data and data["isbn"] is not None:
            value = data["isbn"]
            if not isinstance(value, str):
                errors.append("isbn must be a string")
            else:
                cleaned["isbn"] = value.strip()
        elif "isbn" in data:
            cleaned["isbn"] = None

        return cleaned, errors

    # ----- routes ----------------------------------------------------------

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        cleaned, errors = validate_payload(data, partial=False)
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
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404

        data = request.get_json(silent=True)
        cleaned, errors = validate_payload(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not cleaned:
            return jsonify({"errors": ["no valid fields to update"]}), 400

        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {assignments} WHERE id = ?", values)
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
