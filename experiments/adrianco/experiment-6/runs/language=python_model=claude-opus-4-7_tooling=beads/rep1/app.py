import os
import sqlite3
from flask import Flask, current_app, g, jsonify, request

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db():
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
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


def book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(payload, *, partial=False):
    if not isinstance(payload, dict):
        return "Request body must be a JSON object"

    if not partial:
        if "title" not in payload or not isinstance(payload["title"], str) or not payload["title"].strip():
            return "'title' is required and must be a non-empty string"
        if "author" not in payload or not isinstance(payload["author"], str) or not payload["author"].strip():
            return "'author' is required and must be a non-empty string"
    else:
        if "title" in payload and (not isinstance(payload["title"], str) or not payload["title"].strip()):
            return "'title' must be a non-empty string"
        if "author" in payload and (not isinstance(payload["author"], str) or not payload["author"].strip()):
            return "'author' must be a non-empty string"

    if "year" in payload and payload["year"] is not None:
        if not isinstance(payload["year"], int) or isinstance(payload["year"], bool):
            return "'year' must be an integer"

    if "isbn" in payload and payload["isbn"] is not None:
        if not isinstance(payload["isbn"], str):
            return "'isbn' must be a string"

    return None


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or os.environ.get("DATABASE", DEFAULT_DB_PATH)
    app.teardown_appcontext(close_db)

    init_db(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        payload = request.get_json(silent=True)
        error = validate_book_payload(payload, partial=False)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                payload["title"].strip(),
                payload["author"].strip(),
                payload.get("year"),
                payload.get("isbn"),
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
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        payload = request.get_json(silent=True)
        error = validate_book_payload(payload, partial=True)
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        title = payload["title"].strip() if "title" in payload else row["title"]
        author = payload["author"].strip() if "author" in payload else row["author"]
        year = payload["year"] if "year" in payload else row["year"]
        isbn = payload["isbn"] if "isbn" in payload else row["isbn"]

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return ("", 204)

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
