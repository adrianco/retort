"""Book API REST Service - manages a book collection with CRUD operations."""

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


def book_to_dict(row):
    """Convert a sqlite3.Row to a dictionary."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book():
    """Create a new book entry."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    author = data.get("author")

    if not title or not str(title).strip():
        return jsonify({"error": "Title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "Author is required"}), 400

    year = data.get("year")
    isbn = data.get("isbn")

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({"error": "Year must be an integer"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (str(title).strip(), str(author).strip(), year, isbn),
    )
    db.commit()

    book = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(book_to_dict(book)), 201


@app.route("/books", methods=["GET"])
def list_books():
    """List all books, optionally filtered by author."""
    db = get_db()
    author_filter = request.args.get("author")

    if author_filter:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ?", (f"%{author_filter}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()

    return jsonify([book_to_dict(row) for row in rows]), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Retrieve a single book by ID."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book_to_dict(book)), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    """Update an existing book."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title", book["title"])
    author = data.get("author", book["author"])

    if not str(title).strip():
        return jsonify({"error": "Title is required"}), 400
    if not str(author).strip():
        return jsonify({"error": "Author is required"}), 400

    year = data.get("year", book["year"])
    isbn = data.get("isbn", book["isbn"])

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({"error": "Year must be an integer"}), 400

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (str(title).strip(), str(author).strip(), year, isbn, book_id),
    )
    db.commit()

    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(book_to_dict(updated)), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book by ID."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"message": "Book deleted successfully"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
