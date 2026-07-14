"""Book API REST Service - Flask + plain SQLite."""

import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db():
    """Get a database connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database schema."""
    db = sqlite3.connect(DATABASE)
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
    db.close()


# Health check
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# Create a book
@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    author = data.get("author")

    if not title or not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    year = data.get("year")
    isbn = data.get("isbn")

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({"error": "year must be an integer"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (str(title).strip(), str(author).strip(), year, isbn),
    )
    db.commit()
    book_id = cursor.lastrowid

    return jsonify({"id": book_id, "title": title, "author": author, "year": year, "isbn": isbn}), 201


# List books
@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    db = get_db()

    if author:
        rows = db.execute(
            "SELECT * FROM books WHERE author = ?", (author,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()

    books = [dict(row) for row in rows]
    return jsonify(books), 200


# Get a single book
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(dict(row)), 200


# Update a book
@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title", row["title"])
    author = data.get("author", row["author"])

    if not title or not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    year = data.get("year", row["year"])
    isbn = data.get("isbn", row["isbn"])

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({"error": "year must be an integer"}), 400

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (str(title).strip(), str(author).strip(), year, isbn, book_id),
    )
    db.commit()

    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(dict(updated)), 200


# Delete a book
@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Book not found"}), 404

    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"message": "Book deleted"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
