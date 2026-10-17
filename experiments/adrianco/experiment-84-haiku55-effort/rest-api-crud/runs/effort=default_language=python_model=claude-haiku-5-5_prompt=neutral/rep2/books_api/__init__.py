"""REST API for managing a book collection, backed by SQLite.

Built only on the Python standard library: ``http.server`` for HTTP and
``sqlite3`` for storage.
"""

from .database import BookRepository, ConflictError
from .server import BookAPIServer, create_server
from .validation import ValidationError, validate_book

__all__ = [
    "BookAPIServer",
    "BookRepository",
    "ConflictError",
    "ValidationError",
    "create_server",
    "validate_book",
]
