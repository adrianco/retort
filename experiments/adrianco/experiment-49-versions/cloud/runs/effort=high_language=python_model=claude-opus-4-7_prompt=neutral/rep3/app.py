import os
import sqlite3
from flask import Flask, request, jsonify, g

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(g.db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db(db_path):
    conn = sqlite3.connect(db_path)
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


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_payload(data, partial=False):
    """Return (errors_list, cleaned_dict)."""
    errors = []
    if not isinstance(data, dict):
        return ["request body must be a JSON object"], {}

    cleaned = {}

    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            errors.append("title must be a non-empty string")
        else:
            cleaned["title"] = data["title"].strip()
    elif not partial:
        errors.append("title is required")

    if "author" in data:
        if not isinstance(data["author"], str) or not data["author"].strip():
            errors.append("author must be a non-empty string")
        else:
            cleaned["author"] = data["author"].strip()
    elif not partial:
        errors.append("author is required")

    if "year" in data and data["year"] is not None:
        if not isinstance(data["year"], int) or isinstance(data["year"], bool):
            errors.append("year must be an integer")
        else:
            cleaned["year"] = data["year"]
    elif "year" in data:
        cleaned["year"] = None

    if "isbn" in data and data["isbn"] is not None:
        if not isinstance(data["isbn"], str):
            errors.append("isbn must be a string")
        else:
            cleaned["isbn"] = data["isbn"].strip()
    elif "isbn" in data:
        cleaned["isbn"] = None

    return errors, cleaned


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("BOOKS_DB", DEFAULT_DB)
    init_db(app.config["DB_PATH"])

    @app.before_request
    def _bind_db_path():
        g.db_path = app.config["DB_PATH"]

    @app.teardown_appcontext
    def _close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["request body must be valid JSON"]}), 400
        errors, cleaned = validate_payload(data, partial=False)
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
        return jsonify(book_to_dict(row)), 201

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
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["request body must be valid JSON"]}), 400
        errors, cleaned = validate_payload(data, partial=False)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        existing = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "book not found"}), 404

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned.get("year"),
                cleaned.get("isbn"),
                book_id,
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        existing = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
