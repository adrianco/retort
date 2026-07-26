import os
import sqlite3
from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db(app):
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(app):
    with app.app_context():
        db = get_db(app)
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                title   TEXT    NOT NULL,
                author  TEXT    NOT NULL,
                year    INTEGER,
                isbn    TEXT
            );
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


def _validate_required(payload):
    if not isinstance(payload, dict):
        return "Request body must be a JSON object"
    title = payload.get("title")
    author = payload.get("author")
    if not isinstance(title, str) or not title.strip():
        return "'title' is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return "'author' is required and must be a non-empty string"
    year = payload.get("year")
    if year is not None and not isinstance(year, int):
        return "'year' must be an integer if provided"
    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return "'isbn' must be a string if provided"
    return None


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    init_db(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        payload = request.get_json(silent=True)
        error = _validate_required(payload)
        if error:
            return jsonify({"error": error}), 400

        db = get_db(app)
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                payload["title"].strip(),
                payload["author"].strip(),
                payload.get("year"),
                payload.get("isbn"),
            ),
        )
        db.commit()
        new_id = cursor.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        db = get_db(app)
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db(app)
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        payload = request.get_json(silent=True)
        error = _validate_required(payload)
        if error:
            return jsonify({"error": error}), 400

        db = get_db(app)
        existing = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                payload["title"].strip(),
                payload["author"].strip(),
                payload.get("year"),
                payload.get("isbn"),
                book_id,
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db(app)
        existing = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
