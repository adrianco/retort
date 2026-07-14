"""Flask REST API for managing a book collection."""

import os
import sys

# Ensure the app directory is in the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from models import init_db, create_book, list_books, get_book_by_id, update_book, delete_book

app = Flask(__name__)


def get_db_path():
    """Return the database file path (overridable by tests)."""
    return app.config.get("DATABASE_PATH", "models").__self__ if hasattr(get_db_path, "_path") else _get_real_db_path()


def _get_real_db_path():
    """Get the real default database path from models module."""
    import models as m
    return m.DB_PATH


_real_db_path = None


def _init_db():
    """Initialize the database lazily on first use."""
    global _real_db_path
    if _real_db_path is None:
        import models as m
        _real_db_path = m.DB_PATH
    init_db(_real_db_path)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/books", methods=["POST"])
def create_book_endpoint():
    """Create a new book."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    author = data.get("author")
    year = data.get("year")
    isbn = data.get("isbn")

    if not title:
        return jsonify({"error": "title is required"}), 400
    if not author:
        return jsonify({"error": "author is required"}), 400

    try:
        book = create_book(title=title, author=author, year=year, isbn=isbn)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(book), 201


@app.route("/books", methods=["GET"])
def list_books_endpoint():
    """List all books, optionally filtered by author."""
    author = request.args.get("author")
    books = list_books(author=author)
    return jsonify(books), 200


@app.route("/books/<int:book_id>", methods=["GET"])
def get_book_endpoint(book_id):
    """Get a single book by ID."""
    book = get_book_by_id(book_id)
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book), 200


@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book_endpoint(book_id):
    """Update a book."""
    book = get_book_by_id(book_id)
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title", book["title"])
    author = data.get("author", book["author"])
    year = data.get("year", book["year"])
    isbn = data.get("isbn", book["isbn"])

    if not title:
        return jsonify({"error": "title is required"}), 400
    if not author:
        return jsonify({"error": "author is required"}), 400

    try:
        updated = update_book(book_id=book_id, title=title, author=author, year=year, isbn=isbn)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(updated), 200


@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book_endpoint(book_id):
    """Delete a book."""
    book = get_book_by_id(book_id)
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    delete_book(book_id)
    return jsonify({"message": "Book deleted"}), 200


if __name__ == "__main__":
    _init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
