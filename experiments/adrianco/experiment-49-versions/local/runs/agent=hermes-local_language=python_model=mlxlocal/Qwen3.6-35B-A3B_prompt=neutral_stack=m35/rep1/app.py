"""Book Collection REST API Service."""

import sqlite3
import os
import sys
from contextlib import contextmanager

from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.environ.get("BOOK_DB", os.path.join(os.path.dirname(__file__), "books.db"))


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
    conn = sqlite3.connect(DATABASE)
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


init_db()


@contextmanager
def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        yield None
    else:
        yield dict(row)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    """Create a new book."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    author = data.get("author")

    if not title or not str(title).strip():
        return jsonify({"error": "Title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "Author is required"}), 400

    title = str(title).strip()
    author = str(author).strip()
    year = data.get("year")
    isbn = data.get("isbn")

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn),
    )
    db.commit()
    book_id = cursor.lastrowid

    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(dict(book)), 201


@app.route("/books", methods=["GET"])
def list_books():
    """List all books, optionally filtered by author."""
    author_filter = request.args.get("author")
    db = get_db()

    if author_filter:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ?", (f"%{author_filter}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()

    return jsonify([dict(r) for r in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(dict(book)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title", book["title"])
    author = data.get("author", book["author"])

    if not title or not str(title).strip():
        return jsonify({"error": "Title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "Author is required"}), 400

    title = str(title).strip()
    author = str(author).strip()
    year = data.get("year", book["year"])
    isbn = data.get("isbn", book["isbn"])

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()

    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(dict(updated)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"message": "Book deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
