"""Book Collection REST API - Flask application with SQLite storage."""

import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


def create_app(test_db_path=None):
    """Application factory."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    if test_db_path:
        db_path = test_db_path
    else:
        db_path = os.path.join(base_dir, "books.db")

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db = SQLAlchemy(app)

    class Book(db.Model):
        """A book entry in the collection."""
        __tablename__ = "books"

        id = db.Column(db.Integer, primary_key=True, autoincrement=True)
        title = db.Column(db.String(255), nullable=False)
        author = db.Column(db.String(255), nullable=False)
        year = db.Column(db.Integer, nullable=True)
        isbn = db.Column(db.String(20), nullable=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                               onupdate=datetime.utcnow)

        def to_dict(self):
            return {
                "id": self.id,
                "title": self.title,
                "author": self.author,
                "year": self.year,
                "isbn": self.isbn,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }

    def _validate_book_payload(data):
        """Validate required fields. Returns error string or None."""
        if not data:
            return "Request body must be JSON"
        title = data.get("title")
        author = data.get("author")
        errors = []
        if not title or not str(title).strip():
            errors.append("title is required")
        if not author or not str(author).strip():
            errors.append("author is required")
        if errors:
            return "; ".join(errors)
        return None

    # -------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json()
        error = _validate_book_payload(data)
        if error:
            return jsonify({"error": error}), 400

        title = str(data["title"]).strip()
        author = str(data["author"]).strip()
        year = data.get("year")
        isbn = data.get("isbn")

        if year is not None:
            try:
                year = int(year)
            except (TypeError, ValueError):
                return jsonify({"error": "year must be an integer"}), 400

        book = Book(title=title, author=author, year=year, isbn=isbn)
        db.session.add(book)
        db.session.commit()
        return jsonify(book.to_dict()), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        query = db.session.query(Book)
        if author:
            query = query.filter(Book.author.ilike(f"%{author}%"))
        books = query.all()
        return jsonify([b.to_dict() for b in books]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        book = db.session.get(Book, book_id)
        if book is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book.to_dict()), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        book = db.session.get(Book, book_id)
        if book is None:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        title = data.get("title", book.title)
        author = data.get("author", book.author)
        errors = []
        if not str(title).strip():
            errors.append("title is required")
        if not str(author).strip():
            errors.append("author is required")
        if errors:
            return jsonify({"error": "; ".join(errors)}), 400

        book.title = str(title).strip()
        book.author = str(author).strip()

        if "year" in data:
            try:
                book.year = int(data["year"])
            except (TypeError, ValueError):
                return jsonify({"error": "year must be an integer"}), 400

        if "isbn" in data:
            book.isbn = data["isbn"]

        db.session.commit()
        return jsonify(book.to_dict()), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        book = db.session.get(Book, book_id)
        if book is None:
            return jsonify({"error": "Book not found"}), 404
        db.session.delete(book)
        db.session.commit()
        return jsonify({"message": "Book deleted"}), 200

    return app, db, Book


# Default app instance for running directly.
app, db, Book = create_app()


def _ensure_db():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    _ensure_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
