"""REST API for managing a book collection, backed by SQLite."""

from .app import BookApp
from .store import BookStore

__all__ = ["BookApp", "BookStore"]
