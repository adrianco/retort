import os
import sqlite3
from flask import Flask, jsonify, request, g

DATABASE = os.environ.get("BOOKS_DB", "books.db")


def create_app(database_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database_path or DATABASE

    def get_db():
        db = getattr(g, "_database", None)
        if db is None:
            db = g._database = sqlite3.connect(app.config["DATABASE"])
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

    @app.teardown_appcontext
    def close_db(exception):
        db = getattr(g, "_database", None)
        if db is not None:
            db.close()

    def row_to_dict(row):
        return {k: row[k] for k in row.keys()}

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
        year = data.get("year")
        isbn = data.get("isbn")
        if year is not None and not isinstance(year, int):
            return jsonify({"error": "year must be an integer"}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        db.commit()
        book_id = cur.lastrowid
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute("SELECT * FROM books WHERE author = ?", (author,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM books").fetchall()
        return jsonify([row_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        title = data.get("title", row["title"])
        author = data.get("author", row["author"])
        year = data.get("year", row["year"])
        isbn = data.get("isbn", row["isbn"])
        if not title or not author:
            return jsonify({"error": "title and author are required"}), 400
        if year is not None and not isinstance(year, int):
            return jsonify({"error": "year must be an integer"}), 400
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        db.commit()
        updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(updated)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
