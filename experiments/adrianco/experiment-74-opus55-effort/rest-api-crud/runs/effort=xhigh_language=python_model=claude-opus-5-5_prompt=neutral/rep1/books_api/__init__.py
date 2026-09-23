"""Book collection REST API built on the Python standard library (WSGI + SQLite)."""

from .app import BooksApp, create_app
from .models import Book, BookData
from .repository import BookRepository
from .validation import ValidationError, validate_book

__all__ = [
    "Book",
    "BookData",
    "BookRepository",
    "BooksApp",
    "ValidationError",
    "create_app",
    "validate_book",
]
