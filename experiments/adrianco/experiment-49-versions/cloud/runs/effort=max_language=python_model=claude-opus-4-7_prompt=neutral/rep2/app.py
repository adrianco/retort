"""Book collection REST API — Flask + SQLite."""
import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book(data):
    """Validate a book payload. Returns a dict of field → message errors."""
    errors = {}
    if not isinstance(data, dict):
        return {"_": "payload must be a JSON object"}

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors["title"] = "title is required and must be a non-empty string"

    author = data.get("author")
    if not isinstance(author, str) or not author.strip():
        errors["author"] = "author is required and must be a non-empty string"

    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "year must be an integer"

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"

    return errors


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = os.environ.get("DATABASE_PATH", "books.db")
    if config:
        app.config.update(config)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "request body must be valid JSON"}), 400
        errors = validate_book(data)
        if errors:
            return jsonify({"error": "validation failed", "details": errors}), 400
        db = get_db()
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
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
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
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "request body must be valid JSON"}), 400
        errors = validate_book(data)
        if errors:
            return jsonify({"error": "validation failed", "details": errors}), 400
        db = get_db()
        if db.execute(
            "SELECT 1 FROM books WHERE id = ?", (book_id,)
        ).fetchone() is None:
            return jsonify({"error": "book not found"}), 404
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                data["title"].strip(),
                data["author"].strip(),
                data.get("year"),
                data.get("isbn"),
                book_id,
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        if db.execute(
            "SELECT 1 FROM books WHERE id = ?", (book_id,)
        ).fetchone() is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    @app.errorhandler(404)
    def _not_found(_e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return jsonify({"error": "method not allowed"}), 405

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
