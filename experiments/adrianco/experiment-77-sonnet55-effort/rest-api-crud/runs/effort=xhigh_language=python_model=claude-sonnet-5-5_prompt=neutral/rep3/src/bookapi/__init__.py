"""Book collection REST API."""

from .app import BookApp
from .store import BookStore
from .validation import ValidationError, validate_book

__all__ = ["BookApp", "BookStore", "ValidationError", "validate_book", "create_app"]


def create_app(db_path: str = "books.db") -> BookApp:
    """Build a ready-to-serve WSGI app backed by the SQLite file at ``db_path``."""
    return BookApp(BookStore(db_path))
