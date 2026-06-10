"""Book collection REST API built with Flask and SQLite."""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH

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

    with app.app_context():
        db = sqlite3.connect(app.config["DB_PATH"])
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
        """Return (clean, errors). With partial=True, missing fields are allowed."""
        errors = []
        clean = {}

        if data is None or not isinstance(data, dict):
            return None, ["Request body must be a JSON object."]

        for field in ("title", "author"):
            if field in data:
                value = data[field]
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"'{field}' must be a non-empty string.")
                else:
                    clean[field] = value.strip()
            elif not partial:
                errors.append(f"'{field}' is required.")

        if "year" in data and data["year"] is not None:
            year = data["year"]
            if isinstance(year, bool) or not isinstance(year, int):
                errors.append("'year' must be an integer.")
            else:
                clean["year"] = year
        elif "year" in data:
            clean["year"] = None

        if "isbn" in data and data["isbn"] is not None:
            isbn = data["isbn"]
            if not isinstance(isbn, str) or not isbn.strip():
                errors.append("'isbn' must be a non-empty string.")
            else:
                clean["isbn"] = isbn.strip()
        elif "isbn" in data:
            clean["isbn"] = None

        return clean, errors

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        clean, errors = validate_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (clean["title"], clean["author"], clean.get("year"), clean.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
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
        clean, errors = validate_payload(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not clean:
            return jsonify({"errors": ["No valid fields to update."]}), 400

        fields = ", ".join(f"{k} = ?" for k in clean)
        db.execute(
            f"UPDATE books SET {fields} WHERE id = ?", (*clean.values(), book_id)
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
    def not_found(e):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed."}), 405

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
