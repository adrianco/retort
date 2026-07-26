"""Book collection REST API built with Flask and SQLite."""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def create_app(db_path=DEFAULT_DB_PATH):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)

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

    def book_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_payload(data, partial=False):
        """Return (fields, errors). With partial=True, missing keys are allowed."""
        errors = []
        fields = {}

        if not isinstance(data, dict):
            return None, ["Request body must be a JSON object."]

        for key in ("title", "author"):
            if key in data:
                value = data[key]
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"'{key}' must be a non-empty string.")
                else:
                    fields[key] = value.strip()
            elif not partial:
                errors.append(f"'{key}' is required.")

        if "year" in data:
            value = data["year"]
            if value is None:
                fields["year"] = None
            elif isinstance(value, int) and not isinstance(value, bool):
                fields["year"] = value
            else:
                errors.append("'year' must be an integer or null.")

        if "isbn" in data:
            value = data["isbn"]
            if value is None:
                fields["isbn"] = None
            elif isinstance(value, str):
                fields["isbn"] = value.strip()
            else:
                errors.append("'isbn' must be a string or null.")

        return fields, errors

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["Request body must be valid JSON."]}), 400
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
        return jsonify(book_to_dict(row)), 201

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
        return jsonify([book_to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found."}), 404
        return jsonify(book_to_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found."}), 404

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["Request body must be valid JSON."]}), 400
        fields, errors = validate_payload(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not fields and "year" not in data and "isbn" not in data:
            return jsonify({"errors": ["No updatable fields provided."]}), 400

        current = book_to_dict(row)
        current.update(fields)
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (current["title"], current["author"], current["year"], current["isbn"], book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": f"Book {book_id} not found."}), 404
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
