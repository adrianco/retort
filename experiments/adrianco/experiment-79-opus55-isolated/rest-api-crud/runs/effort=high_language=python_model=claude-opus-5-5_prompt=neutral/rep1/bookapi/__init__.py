"""A small REST API for managing a book collection, backed by SQLite."""

from .app import BookAPI, create_app
from .store import BookStore

__all__ = ["BookAPI", "BookStore", "create_app"]
