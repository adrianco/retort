"""A small REST API for managing a book collection.

Built with Flask and SQLite (via the standard-library ``sqlite3`` module).
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DATABASE = "books.db"


def create_app(database=DATABASE):
    app = Flask(__name__)
    app.config["DATABASE"] = database

    def get_db():
        db = getattr(g, "_database", None)
        if db is None:
            db = g._database = sqlite3.connect(app.config["DATABASE"])
            db.row_factory = sqlite3.Row
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    title   TEXT NOT NULL,
                    author  TEXT NOT NULL,
                    year    INTEGER,
                    isbn    TEXT
                )
                """
            )
            db.commit()
        return db

    @app.teardown_appcontext
    def close_db(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    def book_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_payload(data, *, partial=False):
        """Return (cleaned_fields, error_message).

        When ``partial`` is False (create), title and author are required.
        When ``partial`` is True (update), only supplied fields are validated.
        """
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object"

        fields = {}

        # title / author -- required on create, optional (but non-empty) on update
        for name in ("title", "author"):
            if name in data:
                value = data[name]
                if not isinstance(value, str) or not value.strip():
                    return None, f"'{name}' must be a non-empty string"
                fields[name] = value.strip()
            elif not partial:
                return None, f"'{name}' is required"

        # year -- optional, must be an integer if present
        if "year" in data and data["year"] is not None:
            value = data["year"]
            if isinstance(value, bool) or not isinstance(value, int):
                return None, "'year' must be an integer"
            fields["year"] = value
        elif "year" in data:
            fields["year"] = None

        # isbn -- optional, must be a string if present
        if "isbn" in data and data["isbn"] is not None:
            value = data["isbn"]
            if not isinstance(value, str):
                return None, "'isbn' must be a string"
            fields["isbn"] = value.strip()
        elif "isbn" in data:
            fields["isbn"] = None

        return fields, None

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        fields, error = validate_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                fields["title"],
                fields["author"],
                fields.get("year"),
                fields.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 201

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
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = get_db()
        row = db.execute(
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
        fields, error = validate_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400
        if not fields:
            return jsonify({"error": "No valid fields to update"}), 400

        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values()) + [book_id]
        db.execute(f"UPDATE books SET {assignments} WHERE id = ?", values)
        db.commit()

        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
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
    port = int(os.environ.get("PORT", "5000"))
    create_app().run(host="0.0.0.0", port=port, debug=True)
