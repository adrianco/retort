"""REST API service for managing a book collection, backed by SQLite."""

from .app import BooksApp, create_app
from .db import BookRepository

__all__ = ["BooksApp", "BookRepository", "create_app"]
