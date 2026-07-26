"""A small, dependency-free REST API for managing a book collection."""

from .app import create_app
from .db import Database, BookNotFound
from .validation import ValidationError, parse_book

__version__ = "1.0.0"

__all__ = [
    "create_app",
    "Database",
    "BookNotFound",
    "ValidationError",
    "parse_book",
    "__version__",
]
