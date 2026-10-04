"""A small REST API for managing a book collection, backed by SQLite."""

from bookapi.app import BookAPI
from bookapi.store import BookStore

__all__ = ["BookAPI", "BookStore"]
