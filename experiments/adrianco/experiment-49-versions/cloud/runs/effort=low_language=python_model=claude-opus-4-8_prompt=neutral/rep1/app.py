"""A REST API service for managing a book collection."""
import os
import sqlite3

from flask import Flask, g, jsonify, request

DATABASE = os.environ.get("BOOKS_DB", "books.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(current_db_path())
        db.row_factory = sqlite3.Row
    return db


def current_db_path():
    return app.config.get("DATABASE", DATABASE)


def init_db(db_path=None):
    conn = sqlite3.connect(db_path or current_db_path())
    conn.execute(
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
    conn.commit()
    conn.close()


def create_app(database=None):
    global app
    app = Flask(__name__)
    app.config["DATABASE"] = database or DATABASE

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
        """Return (cleaned_dict, error_message)."""
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object"

        errors = []
        cleaned = {}

        for field in ("title", "author"):
            if field in data:
                value = data[field]
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"'{field}' must be a non-empty string")
                else:
                    cleaned[field] = value.strip()
            elif not partial:
                errors.append(f"'{field}' is required")

        if "year" in data and data["year"] is not None:
            year = data["year"]
            if not isinstance(year, int) or isinstance(year, bool):
                errors.append("'year' must be an integer")
            else:
                cleaned["year"] = year
        elif "year" in data:
            cleaned["year"] = None

        if "isbn" in data:
            isbn = data["isbn"]
            if isbn is not None and not isinstance(isbn, str):
                errors.append("'isbn' must be a string")
            else:
                cleaned["isbn"] = isbn

        if errors:
            return None, "; ".join(errors)
        return cleaned, None

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

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
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        cleaned, error = validate_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400
        if not cleaned:
            return jsonify({"error": "No valid fields to update"}), 400

        columns = ", ".join(f"{k} = ?" for k in cleaned)
        values = list(cleaned.values()) + [book_id]
        db.execute(f"UPDATE books SET {columns} WHERE id = ?", values)
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


app = create_app()

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
