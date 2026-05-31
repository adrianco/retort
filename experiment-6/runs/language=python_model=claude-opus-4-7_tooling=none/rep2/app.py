import os
import sqlite3
from flask import Flask, g, jsonify, request

DATABASE = os.environ.get("BOOKS_DB", "books.db")


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


def validate_book_payload(data, partial=False):
    if not isinstance(data, dict):
        return "Request body must be a JSON object"

    if not partial:
        if "title" not in data or not isinstance(data.get("title"), str) or not data["title"].strip():
            return "Field 'title' is required and must be a non-empty string"
        if "author" not in data or not isinstance(data.get("author"), str) or not data["author"].strip():
            return "Field 'author' is required and must be a non-empty string"
    else:
        if "title" in data and (not isinstance(data["title"], str) or not data["title"].strip()):
            return "Field 'title' must be a non-empty string"
        if "author" in data and (not isinstance(data["author"], str) or not data["author"].strip()):
            return "Field 'author' must be a non-empty string"

    if "year" in data and data["year"] is not None and not isinstance(data["year"], int):
        return "Field 'year' must be an integer"
    if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
        return "Field 'isbn' must be a string"
    return None


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or DATABASE
    init_db(app.config["DATABASE"])

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    def db_conn():
        db = getattr(g, "_database", None)
        if db is None:
            db = g._database = sqlite3.connect(app.config["DATABASE"])
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
        return db

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400
        error = validate_book_payload(data, partial=False)
        if error:
            return jsonify({"error": error}), 400

        conn = db_conn()
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                data["title"].strip(),
                data["author"].strip(),
                data.get("year"),
                data.get("isbn"),
            ),
        )
        conn.commit()
        book_id = cur.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        conn = db_conn()
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        conn = db_conn()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400
        error = validate_book_payload(data, partial=True)
        if error:
            return jsonify({"error": error}), 400

        conn = db_conn()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        title = data["title"].strip() if "title" in data else row["title"]
        author = data["author"].strip() if "author" in data else row["author"]
        year = data["year"] if "year" in data else row["year"]
        isbn = data["isbn"] if "isbn" in data else row["isbn"]

        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        conn = db_conn()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return "", 204

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
