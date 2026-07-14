import os
import sqlite3
from flask import Flask, request, jsonify, g

DATABASE = os.environ.get("BOOKS_DB", "books.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(db_path=None):
    path = db_path or DATABASE
    conn = sqlite3.connect(path)
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


def row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_app(database=None):
    app = Flask(__name__)
    if database is not None:
        app.config["DATABASE"] = database
    else:
        app.config["DATABASE"] = DATABASE

    init_db(app.config["DATABASE"])

    @app.before_request
    def _bind_db():
        g._db_path = app.config["DATABASE"]

    def _connect():
        db = getattr(g, "_database", None)
        if db is None:
            db = g._database = sqlite3.connect(app.config["DATABASE"])
            db.row_factory = sqlite3.Row
        return db

    @app.teardown_appcontext
    def _close(_exc):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True) or {}
        title = data.get("title")
        author = data.get("author")
        if not isinstance(title, str) or not title.strip():
            return jsonify({"error": "title is required"}), 400
        if not isinstance(author, str) or not author.strip():
            return jsonify({"error": "author is required"}), 400

        year = data.get("year")
        if year is not None and not isinstance(year, int):
            return jsonify({"error": "year must be an integer"}), 400
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return jsonify({"error": "isbn must be a string"}), 400

        db = _connect()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title.strip(), author.strip(), year, isbn),
        )
        db.commit()
        book_id = cur.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = _connect()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_book(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = _connect()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_book(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        db = _connect()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404

        title = data.get("title", row["title"])
        author = data.get("author", row["author"])
        if not isinstance(title, str) or not title.strip():
            return jsonify({"error": "title is required"}), 400
        if not isinstance(author, str) or not author.strip():
            return jsonify({"error": "author is required"}), 400

        year = data.get("year", row["year"])
        if year is not None and not isinstance(year, int):
            return jsonify({"error": "year must be an integer"}), 400
        isbn = data.get("isbn", row["isbn"])
        if isbn is not None and not isinstance(isbn, str):
            return jsonify({"error": "isbn must be a string"}), 400

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title.strip(), author.strip(), year, isbn, book_id),
        )
        db.commit()
        updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = _connect()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
