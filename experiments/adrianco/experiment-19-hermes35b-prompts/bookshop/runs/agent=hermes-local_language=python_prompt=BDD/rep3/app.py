"""
Flask REST API for managing a book collection.
"""
import os
import models
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    author = data.get("author")
    if not title or not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title is required and must be a non-empty string"}), 400
    if not author or not isinstance(author, str) or not author.strip():
        return jsonify({"error": "author is required and must be a non-empty string"}), 400
    year = data.get("year")
    isbn = data.get("isbn")
    book = models.insert_book(title.strip(), author.strip(), year, isbn)
    return jsonify(book), 201

@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    books = models.select_all_books(author=author)
    return jsonify(books), 200

@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    book = models.select_book_by_id(book_id)
    if book is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(book), 200

@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    existing = models.select_book_by_id(book_id)
    if existing is None:
        return jsonify({"error": "book not found"}), 404
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    author = data.get("author")
    if title is not None and (not isinstance(title, str) or not title.strip()):
        return jsonify({"error": "title must be a non-empty string"}), 400
    if author is not None and (not isinstance(author, str) or not author.strip()):
        return jsonify({"error": "author must be a non-empty string"}), 400
    year = data.get("year")
    isbn = data.get("isbn")
    updated = models.update_book(
        book_id,
        title=title.strip() if title is not None else None,
        author=author.strip() if author is not None else None,
        year=year,
        isbn=isbn,
    )
    if updated is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(updated), 200

@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    deleted = models.delete_book(book_id)
    if not deleted:
        return jsonify({"error": "book not found"}), 404
    return jsonify({"message": "book deleted"}), 200

if __name__ == "__main__":
    models.init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
