"""Database models for the Book API."""
from datetime import datetime

from app import db


class Book(db.Model):
    """Represents a book in the collection."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(500), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    isbn = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Serialize the book to a dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "isbn": self.isbn,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Book {self.title} by {self.author}>"
