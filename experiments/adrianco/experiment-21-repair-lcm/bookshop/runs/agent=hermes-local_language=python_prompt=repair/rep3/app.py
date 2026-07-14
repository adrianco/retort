"""Book Collection REST API service."""

import os
import sqlite3
from flask import Flask, g, request, jsonify

app = Flask(__name__)

DATABASE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db"))


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
    """Initialize the database with the books table."""
    db = sqlite3.connect(DATABASE)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
        """
    )
    db.commit()
    db.close()


@app.before_request
def before_request():
    """Ensure the database is initialised before each request."""
    init_db()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# POST /books - Create a new book
# ---------------------------------------------------------------------------

@app.route("/books", methods=["POST"])
def create_book():
    """Create a new book entry."""
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
        except (TypeError, ValueError):
            return jsonify({"error": "year must be an integer"}), 400

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        db.commit()
        book_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "A book with this ISBN already exists"}), 409

    return jsonify({"id": book_id, "title": title, "author": author, "year": year, "isbn": isbn}), 201


# ---------------------------------------------------------------------------
# GET /books - List all books (optional ?author= filter)
# ---------------------------------------------------------------------------

@app.route("/books", methods=["GET"])
def list_books():
    """List all books, optionally filtered by author."""
    author_filter = request.args.get("author")
    db = get_db()

    if author_filter:
        rows = db.execute(
            "SELECT * FROM books WHERE author LIKE ?",
            (f"%{author_filter}%",),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books").fetchall()

    books = [
        {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }
        for row in rows
    ]
    return jsonify(books), 200


# ---------------------------------------------------------------------------
# GET /books/<int:id> - Get a single book
# ---------------------------------------------------------------------------

@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    """Retrieve a single book by its ID."""
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    return jsonify(
        {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }
    ), 200


# ---------------------------------------------------------------------------
# PUT /books/<int:id> - Update a book
# ---------------------------------------------------------------------------

@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    """Update an existing book entry."""
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title", row["title"])
    author = data.get("author", row["author"])
    year = data.get("year", row["year"])
    isbn = data.get("isbn", row["isbn"])

    if not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    if year is not None and year != row["year"]:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return jsonify({"error": "year must be an integer"}), 400

    try:
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "A book with this ISBN already exists"}), 409

    return jsonify({"id": book_id, "title": title, "author": author, "year": year, "isbn": isbn}), 200


# ---------------------------------------------------------------------------
# DELETE /books/<int:id> - Delete a book
# ---------------------------------------------------------------------------

@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book by its ID."""
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()

    return jsonify({"message": "Book deleted"}), 200


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
