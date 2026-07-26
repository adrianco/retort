"""A small REST API for managing a book collection.

Uses Flask for the web layer and SQLite for storage.
"""
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
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

    def validate_payload(data, partial=False):
        """Return (cleaned, error). For create, title and author are required.

        With partial=True (PUT), only validate the fields that are present.
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
            year = data["year"]
            if not isinstance(year, int) or isinstance(year, bool):
                return None, "'year' must be an integer"
            cleaned["year"] = year
        elif "year" in data:
            cleaned["year"] = None

        if "isbn" in data:
            isbn = data["isbn"]
            if isbn is not None and not isinstance(isbn, str):
                return None, "'isbn' must be a string"
            cleaned["isbn"] = isbn

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
        cleaned, error = validate_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400

        if not cleaned:
            return jsonify({"error": "No fields to update"}), 400

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
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
