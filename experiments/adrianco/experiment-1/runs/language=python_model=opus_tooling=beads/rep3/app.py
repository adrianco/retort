import os
import sqlite3
from flask import Flask, request, jsonify, g

DEFAULT_DB = os.path.join(os.path.dirname(__file__), "books.db")


def get_db(app):
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
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


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", DEFAULT_DB)

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
        data = request.get_json(silent=True) or {}
        title = data.get("title")
        author = data.get("author")
        if not title or not isinstance(title, str) or not title.strip():
            return jsonify({"error": "title is required"}), 400
        if not author or not isinstance(author, str) or not author.strip():
            return jsonify({"error": "author is required"}), 400
        year = data.get("year")
        isbn = data.get("isbn")
        db = get_db(app)
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db(app)
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
            return jsonify({"error": "not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        db = get_db(app)
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        title = data.get("title", row["title"])
        author = data.get("author", row["author"])
        year = data.get("year", row["year"])
        isbn = data.get("isbn", row["isbn"])
        if not title or not isinstance(title, str) or not title.strip():
            return jsonify({"error": "title is required"}), 400
        if not author or not isinstance(author, str) or not author.strip():
            return jsonify({"error": "author is required"}), 400
        db.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (title, author, year, isbn, book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db(app)
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
