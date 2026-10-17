"""Book collection REST API backed by SQLite (standard library only)."""

from .server import create_server
from .storage import BookStore
from .validation import ValidationError, validate_book

__all__ = ["create_server", "BookStore", "ValidationError", "validate_book"]
