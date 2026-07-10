"""Book API REST Service.

A minimal REST API for managing a book collection, backed by SQLite via Flask-SQLAlchemy.
"""

import os

from flask import Flask, abort, jsonify, request
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)

    # In-memory SQLite for testing, persistent SQLite for production
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///books.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if app.config["TESTING"]:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"  # in-memory

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # ─── Routes ───────────────────────────────────────────────────────────

    @app.route("/health", methods=["GET"])
    def health():
        """Health check — returns 200 with status information."""
        return jsonify({"status": "healthy"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        """Create a new book.

        Expects JSON body with at least 'title' and 'author'.
        Optional fields: 'year' (int), 'isbn' (str).
        """
        data = request.get_json(silent=True)
        if not data:
            abort(400, description="Request body must be valid JSON")

        title = data.get("title")
        author = data.get("author")

        if not title or not str(title).strip():
            abort(400, description="Title is required and must not be empty")
        if not author or not str(author).strip():
            abort(400, description="Author is required and must not be empty")

        book = Book(
            title=str(title).strip(),
            author=str(author).strip(),
            year=data.get("year"),
            isbn=data.get("isbn"),
        )
        db.session.add(book)
        db.session.commit()

        return jsonify({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
        }), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        """List all books, optionally filtered by author (?author=xxx)."""
        author_filter = request.args.get("author")
        if author_filter:
            books = Book.query.filter(
                Book.author.ilike(f"%{author_filter}%")
            ).all()
        else:
            books = Book.query.all()

        return jsonify([
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "year": b.year,
                "isbn": b.isbn,
            }
            for b in books
        ]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        """Get a single book by ID."""
        book = db.session.get(Book, book_id)
        if book is None:
            abort(404, description="Book not found")
        return jsonify({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
        }), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        """Update an existing book."""
        book = db.session.get(Book, book_id)
        if book is None:
            abort(404, description="Book not found")

        data = request.get_json(silent=True)
        if not data:
            abort(400, description="Request body must be valid JSON")

        # Validate title if provided
        if "title" in data:
            title = data["title"]
            if not title or not str(title).strip():
                abort(400, description="Title must not be empty")
            book.title = str(title).strip()

        # Validate author if provided
        if "author" in data:
            author = data["author"]
            if not author or not str(author).strip():
                abort(400, description="Author must not be empty")
            book.author = str(author).strip()

        if "year" in data:
            book.year = data["year"]
        if "isbn" in data:
            book.isbn = data["isbn"]

        db.session.commit()

        return jsonify({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
        }), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        """Delete a book by ID."""
        book = db.session.get(Book, book_id)
        if book is None:
            abort(404, description="Book not found")
        db.session.delete(book)
        db.session.commit()
        return jsonify({"message": "Book deleted"}), 200

    return app


# ─── Database model ─────────────────────────────────────────────────────────


class Book(db.Model):
    """Book entity stored in the SQLite database."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(500), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    isbn = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "isbn": self.isbn,
        }


# ─── Entry point ────────────────────────────────────────────────────────────


def get_db():
    """Return the SQLAlchemy db instance (helper for tests)."""
    return db


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
