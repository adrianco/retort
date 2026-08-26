"""Book API REST Service - Manage a collection of books with CRUD operations."""

import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Use an environment variable for the database path, default to books.db
    db_path = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')}",
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db = SQLAlchemy(app)

    class Book(db.Model):
        """Book model for the collection."""

        id = db.Column(db.Integer, primary_key=True, autoincrement=True)
        title = db.Column(db.String(200), nullable=False)
        author = db.Column(db.String(200), nullable=False)
        year = db.Column(db.Integer, nullable=True)
        isbn = db.Column(db.String(13), nullable=True)

        def to_dict(self):
            """Convert book instance to dictionary."""
            return {
                "id": self.id,
                "title": self.title,
                "author": self.author,
                "year": self.year,
                "isbn": self.isbn,
            }

    # Initialize tables
    with app.app_context():
        db.create_all()

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({"status": "healthy"}), 200

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

        book = Book(
            title=str(title).strip(),
            author=str(author).strip(),
            year=data.get("year"),
            isbn=data.get("isbn"),
        )

        db.session.add(book)
        db.session.commit()

        return jsonify(book.to_dict()), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        """List all books, optionally filtered by author."""
        author_filter = request.args.get("author")

        query = Book.query

        if author_filter:
            query = query.filter(Book.author.ilike(f"%{author_filter}%"))

        books = query.all()
        return jsonify([book.to_dict() for book in books]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        """Get a single book by ID."""
        book = db.session.get(Book, book_id)

        if not book:
            return jsonify({"error": "Book not found"}), 404

        return jsonify(book.to_dict()), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        """Update a book."""
        book = db.session.get(Book, book_id)

        if not book:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        title = data.get("title")
        author = data.get("author")

        if title is not None:
            if not str(title).strip():
                return jsonify({"error": "Title cannot be empty"}), 400
            book.title = str(title).strip()

        if author is not None:
            if not str(author).strip():
                return jsonify({"error": "Author cannot be empty"}), 400
            book.author = str(author).strip()

        if "year" in data:
            book.year = data["year"]

        if "isbn" in data:
            book.isbn = data["isbn"]

        db.session.commit()

        return jsonify(book.to_dict()), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        """Delete a book."""
        book = db.session.get(Book, book_id)

        if not book:
            return jsonify({"error": "Book not found"}), 404

        db.session.delete(book)
        db.session.commit()

        return jsonify({"message": "Book deleted successfully"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
