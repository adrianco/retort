"""A small REST API for managing a book collection, backed by SQLite."""

from .app import BooksApp, Response
from .db import BookRepository
from .server import create_server, main
from .validation import ValidationError, validate_book

__all__ = [
    "BookRepository",
    "BooksApp",
    "Response",
    "ValidationError",
    "create_server",
    "main",
    "validate_book",
]
__version__ = "1.0.0"
