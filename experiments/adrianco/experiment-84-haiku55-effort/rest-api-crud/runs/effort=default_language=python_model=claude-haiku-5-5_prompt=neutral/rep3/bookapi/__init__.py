"""Book collection REST API backed by SQLite (standard library only)."""

from .http_app import BookAPIServer, create_server
from .store import BookStore
from .validation import ValidationError, validate_book

__all__ = ["BookAPIServer", "BookStore", "ValidationError", "create_server", "validate_book"]
