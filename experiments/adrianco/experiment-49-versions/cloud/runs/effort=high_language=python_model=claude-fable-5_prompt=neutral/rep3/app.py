"""Book collection REST API backed by SQLite."""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


def create_app(db_path=DEFAULT_DB_PATH):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    with sqlite3.connect(db_path) as conn:
        conn.execute(SCHEMA)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
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
        """Return (fields, errors). With partial=True only validate present keys."""
        errors = []
        fields = {}

        if not isinstance(data, dict):
            return None, ["request body must be a JSON object"]

        for key in ("title", "author"):
            if key in data or not partial:
                value = data.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"'{key}' is required and must be a non-empty string")
                else:
                    fields[key] = value.strip()

        if "year" in data:
            year = data["year"]
            if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
                errors.append("'year' must be an integer or null")
            else:
                fields["year"] = year

        if "isbn" in data:
            isbn = data["isbn"]
            if isbn is not None and not isinstance(isbn, str):
                errors.append("'isbn' must be a string or null")
            else:
                fields["isbn"] = isbn

        return fields, errors

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["request body must be valid JSON"]}), 400
        fields, errors = validate_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (fields["title"], fields["author"], fields.get("year"), fields.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["request body must be valid JSON"]}), 400
        fields, errors = validate_payload(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not fields:
            return jsonify({"errors": ["no updatable fields provided"]}), 400

        assignments = ", ".join(f"{key} = ?" for key in fields)
        db.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*fields.values(), book_id),
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
            return jsonify({"error": "book not found"}), 404
        return "", 204

    @app.errorhandler(404)
    def not_found(exc):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(exc):
        return jsonify({"error": "method not allowed"}), 405

    return app


if __name__ == "__main__":
    # Port 5000 is taken by AirPlay Receiver on recent macOS, so default to 8000.
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 8000)))
