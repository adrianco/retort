import os
import sqlite3
from flask import Flask, g, jsonify, request

DB_PATH = os.environ.get("BOOKS_DB", "books.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )"""
    )
    conn.commit()
    conn.close()


def row_to_dict(row):
    return {k: row[k] for k in row.keys()}


def create_app(db_path=None):
    app = Flask(__name__)
    if db_path:
        app.config["DB_PATH"] = db_path
        global DB_PATH
        DB_PATH = db_path
    init_db(db_path)

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

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
        if year is not None and not isinstance(year, int):
            return jsonify({"error": "year must be an integer"}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title.strip(), author.strip(), year, isbn),
        )
        db.commit()
        book_id = cur.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row)), 201

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
        return jsonify([row_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(row_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        current = row_to_dict(row)
        title = data.get("title", current["title"])
        author = data.get("author", current["author"])
        year = data.get("year", current["year"])
        isbn = data.get("isbn", current["isbn"])
        if not title or not isinstance(title, str) or not title.strip():
            return jsonify({"error": "title is required"}), 400
        if not author or not isinstance(author, str) or not author.strip():
            return jsonify({"error": "author is required"}), 400
        if year is not None and not isinstance(year, int):
            return jsonify({"error": "year must be an integer"}), 400
        db.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (title.strip(), author.strip(), year, isbn, book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
