"""Flask application for managing a book collection.

This implementation satisfies the requirements from TASK.md using Flask and SQLAlchemy.
"""

import os
from flask import Flask, jsonify, request, abort
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# Models
Base = declarative_base()

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer)
    isbn = Column(String)

# Database setup
DATABASE_URL = os.path.join(os.getcwd(), "books.db")
engine = create_engine(f"sqlite:///{DATABASE_URL}", connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = scoped_session(sessionmaker(bind=engine))

app = Flask(__name__)

# Health check
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# CRUD endpoints
@app.route("/books", methods=["POST"])
def create_book():
    data = request.get_json()
    if not data or "title" not in data or "author" not in data:
        abort(400, description="Missing required fields: title, author")
    book = Book(**{k: data.get(k) for k in ["title", "author", "year", "isbn"]})
    db = SessionLocal()
    db.add(book)
    db.commit()
    db.refresh(book)
    db.close()
    return jsonify({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
    }), 201

@app.route("/books", methods=["GET"])
def list_books():
    author = request.args.get("author")
    db = SessionLocal()
    query = db.query(Book)
    if author:
        query = query.filter(Book.author == author)
    books = query.all()
    db.close()
    return jsonify([
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "year": b.year,
            "isbn": b.isbn,
        }
        for b in books
    ])

@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    db = SessionLocal()
    book = db.get(Book, book_id)
    db.close()
    if not book:
        abort(404, description="Book not found")
    return jsonify({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
    })

@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json() or {}
    db = SessionLocal()
    book = db.get(Book, book_id)
    if not book:
        db.close()
        abort(404, description="Book not found")
    for field in ["title", "author", "year", "isbn"]:
        if field in data:
            setattr(book, field, data[field])
    db.commit()
    db.refresh(book)
    db.close()
    return jsonify({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
    })

@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    db = SessionLocal()
    book = db.get(Book, book_id)
    if not book:
        db.close()
        abort(404, description="Book not found")
    db.delete(book)
    db.commit()
    db.close()
    return '', 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
