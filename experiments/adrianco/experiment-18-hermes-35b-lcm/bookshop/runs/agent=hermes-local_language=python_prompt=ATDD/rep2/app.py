"""Book API REST Service - Flask application."""
import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    """Application factory."""
    app = Flask(__name__)

    # Database configuration
    database_uri = os.environ.get("DATABASE_URI", "sqlite:///books.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False

    db.init_app(app)

    with app.app_context():
        from models import Book
        db.create_all()

    # Health check
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    # Create a book
    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        title = data.get("title")
        author = data.get("author")

        if not title or not str(title).strip():
            return jsonify({"error": "Title is required and cannot be empty"}), 400
        if not author or not str(author).strip():
            return jsonify({"error": "Author is required and cannot be empty"}), 400

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

    # List all books
    @app.route("/books", methods=["GET"])
    def list_books():
        author_filter = request.args.get("author")
        if author_filter:
            books = Book.query.filter_by(author=author_filter).all()
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

    # Get a single book
    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        book = Book.query.get(book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404

        return jsonify({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
        }), 200

    # Update a book
    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        book = Book.query.get(book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        if "title" in data:
            title = str(data["title"]).strip()
            if not title:
                return jsonify({"error": "Title cannot be empty"}), 400
            book.title = title

        if "author" in data:
            author = str(data["author"]).strip()
            if not author:
                return jsonify({"error": "Author cannot be empty"}), 400
            book.author = author

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

    # Delete a book
    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        book = Book.query.get(book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404

        db.session.delete(book)
        db.session.commit()

        return jsonify({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
        }), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
