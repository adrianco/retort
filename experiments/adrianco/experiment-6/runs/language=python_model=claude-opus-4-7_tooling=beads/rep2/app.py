import os
import sqlite3
from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db(app):
    db = g.get("_database")
    if db is None:
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g._database = db
    return db


def init_db(app):
    with app.app_context():
        db = get_db(app)
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


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(data, *, partial=False):
    if not isinstance(data, dict):
        return "Request body must be a JSON object"

    required = ("title", "author")
    if not partial:
        for field in required:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                return f"'{field}' is required and must be a non-empty string"
    else:
        for field in required:
            if field in data:
                value = data[field]
                if not isinstance(value, str) or not value.strip():
                    return f"'{field}' must be a non-empty string"

    if "year" in data and data["year"] is not None:
        if not isinstance(data["year"], int) or isinstance(data["year"], bool):
            return "'year' must be an integer"

    if "isbn" in data and data["isbn"] is not None:
        if not isinstance(data["isbn"], str):
            return "'isbn' must be a string"

    return None


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("_database", None)
        if db is not None:
            db.close()

    init_db(app)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        error = validate_book_payload(data)
        if error:
            return jsonify({"error": error}), 400

        db = get_db(app)
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                data["title"].strip(),
                data["author"].strip(),
                data.get("year"),
                data.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = get_db(app)
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = get_db(app)
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
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

        db = get_db(app)
        existing = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404

        merged = {
            "title": data["title"].strip() if "title" in data else existing["title"],
            "author": data["author"].strip() if "author" in data else existing["author"],
            "year": data["year"] if "year" in data else existing["year"],
            "isbn": data["isbn"] if "isbn" in data else existing["isbn"],
        }

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db(app)
        existing = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return ("", 204)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
