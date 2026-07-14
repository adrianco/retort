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


# --- Health Check ---

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


# --- Create Book ---

@app.route("/books", methods=["POST"])
def create_book():
    """Create a new book."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    author = data.get("author")

    if not title or not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    title = str(title).strip()
    author = str(author).strip()
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
        (title, author, year, isbn),
    )
    db.commit()
    new_id = cursor.lastrowid

    book = db.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
    return jsonify(book_to_dict(book)), 201


# --- List Books ---

@app.route("/books", methods=["GET"])
def list_books():
    """List all books, optionally filtered by author."""
    author = request.args.get("author")
    db = get_db()

    if author:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ?", (f"%{author}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()

    return jsonify([book_to_dict(row) for row in rows]), 200


# --- Get Single Book ---

@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book_to_dict(book)), 200


# --- Update Book ---

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

    if not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    title = str(title).strip()
    author = str(author).strip()
    year = data.get("year", book["year"])
    isbn = data.get("isbn", book["isbn"])

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({"error": "year must be an integer"}), 400

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    db.commit()

    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(book_to_dict(updated)), 200


# --- Delete Book ---

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


# --- Main ---

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
