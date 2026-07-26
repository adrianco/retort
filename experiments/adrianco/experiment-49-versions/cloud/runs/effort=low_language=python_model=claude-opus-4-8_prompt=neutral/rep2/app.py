"""A REST API service for managing a book collection.

Uses Flask with an embedded SQLite database.
"""
import sqlite3
from flask import Flask, request, jsonify, g

DATABASE = "books.db"


def create_app(database=DATABASE):
    app = Flask(__name__)
    app.config["DATABASE"] = database

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
            """
        )
        db.commit()

    with app.app_context():
        init_db()

    def book_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_payload(data, partial=False):
        """Return (cleaned, error). For non-partial, title and author required."""
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object"
        cleaned = {}
        for field in ("title", "author", "year", "isbn"):
            if field in data:
                cleaned[field] = data[field]
        if not partial:
            for req in ("title", "author"):
                val = cleaned.get(req)
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    return None, f"'{req}' is required"
        else:
            for req in ("title", "author"):
                if req in cleaned:
                    val = cleaned[req]
                    if val is None or (isinstance(val, str) and val.strip() == ""):
                        return None, f"'{req}' cannot be empty"
        if "year" in cleaned and cleaned["year"] is not None:
            if not isinstance(cleaned["year"], int) or isinstance(cleaned["year"], bool):
                return None, "'year' must be an integer"
        return cleaned, None

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        cleaned, error = validate_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400
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
        return jsonify(book_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ?", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books").fetchall()
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
        cleaned, error = validate_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400
        merged = book_to_dict(row)
        merged.update(cleaned)
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                merged["title"],
                merged["author"],
                merged["year"],
                merged["isbn"],
                book_id,
            ),
        )
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
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
