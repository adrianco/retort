import os
import sqlite3
from flask import Flask, request, jsonify, g, current_app


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute(
            """CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )"""
        )
        db.commit()
    return db


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
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", "books.db")

    @app.teardown_appcontext
    def close_connection(exception):
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
        if not title or not author:
            return jsonify({"error": "title and author are required"}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, data.get("year"), data.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id=?", (cur.lastrowid,)).fetchone()
        return jsonify(book_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute("SELECT * FROM books WHERE author=?", (author,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM books").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        title = data.get("title", row["title"])
        author = data.get("author", row["author"])
        if not title or not author:
            return jsonify({"error": "title and author are required"}), 400
        year = data.get("year", row["year"])
        isbn = data.get("isbn", row["isbn"])
        db.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (title, author, year, isbn, book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return jsonify(book_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
