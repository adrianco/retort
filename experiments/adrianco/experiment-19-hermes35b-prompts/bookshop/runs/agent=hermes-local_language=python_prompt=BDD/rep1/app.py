"""
Book API REST Service - Main Application
A REST API for managing a book collection with CRUD operations.
"""

import os
import sqlite3
from flask import Flask, request, jsonify, g

app = Flask(__name__)

# Database configuration
DB_PATH = os.environ.get("BOOK_DB_PATH", "books.db")


def get_db():
    """Get database connection for current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database schema."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    """)
    conn.commit()
    conn.close()


@app.before_request
def before_request():
    """Ensure database is initialized."""
    init_db()


# --- Health Check ---
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


# --- Create a Book ---
@app.route("/books", methods=["POST"])
def create_book():
    """Create a new book.

    Required fields: title, author
    Optional fields: year, isbn
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    author = data.get("author")

    # Validation: title and author are required
    if title is None or not str(title).strip():
        return jsonify({"error": "Title is required"}), 400

    if author is None or not str(author).strip():
        return jsonify({"error": "Author is required"}), 400

    year = data.get("year")
    isbn = data.get("isbn")

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (str(title).strip(), str(author).strip(), year, isbn),
    )
    db.commit()

    book_id = cursor.lastrowid

    return (
        jsonify(
            {
                "id": book_id,
                "title": str(title).strip(),
                "author": str(author).strip(),
                "year": year,
                "isbn": isbn,
            }
        ),
        201,
    )


# --- List all books (with optional author filter) ---
@app.route("/books", methods=["GET"])
def list_books():
    """List all books, with optional ?author= filter."""
    author_filter = request.args.get("author")
    db = get_db()

    if author_filter:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ?", (f"%{author_filter}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()

    books = [dict(row) for row in rows]
    return jsonify(books), 200


# --- Get a single book ---
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    return jsonify(dict(row)), 200


# --- Update a book ---
@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    """Update an existing book."""
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Title and author are required fields on update (must be explicitly provided)
    if "title" not in data:
        return jsonify({"error": "Title is required"}), 400
    if "author" not in data:
        return jsonify({"error": "Author is required"}), 400

    title = data["title"]
    author = data["author"]
    year = data.get("year", row["year"])
    isbn = data.get("isbn", row["isbn"])

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (str(title).strip(), str(author).strip(), year, isbn, book_id),
    )
    db.commit()

    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(dict(updated)), 200


# --- Delete a book ---
@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()

    return jsonify({"message": "Book deleted successfully"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
