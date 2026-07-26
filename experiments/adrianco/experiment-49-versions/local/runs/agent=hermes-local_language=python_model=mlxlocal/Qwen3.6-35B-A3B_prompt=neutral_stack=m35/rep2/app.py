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
    """Initialize the database and create the books table if it doesn't exist."""
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


def row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


# --- Health check ---

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


# --- Create a book ---

@app.route("/books", methods=["POST"])
def create_book():
    """Create a new book.

    Expected JSON body:
        {
            "title": "string (required)",
            "author": "string (required)",
            "year": integer (optional),
            "isbn": string (optional)
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

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
    book_id = cursor.lastrowid

    book = row_to_dict(db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone())
    return jsonify(book), 201


# --- List all books (with optional author filter) ---

@app.route("/books", methods=["GET"])
def list_books():
    """List all books. Supports ?author= filter."""
    db = get_db()
    author_filter = request.args.get("author")

    if author_filter:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ?", (f"%{author_filter}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()

    books = [row_to_dict(row) for row in rows]
    return jsonify(books), 200


# --- Get a single book by ID ---

@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(row_to_dict(book)), 200


# --- Update a book ---

@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    """Update an existing book.

    Expected JSON body (all fields optional, but at least one required):
        {
            "title": "string",
            "author": "string",
            "year": integer,
            "isbn": string
        }
    """
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    title = data.get("title", book["title"])
    author = data.get("author", book["author"])

    if not str(title).strip():
        return jsonify({"error": "title cannot be empty"}), 400
    if not str(author).strip():
        return jsonify({"error": "author cannot be empty"}), 400

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

    updated = row_to_dict(
        db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    )
    return jsonify(updated), 200


# --- Delete a book ---

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


# --- Initialize DB on startup ---
init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
