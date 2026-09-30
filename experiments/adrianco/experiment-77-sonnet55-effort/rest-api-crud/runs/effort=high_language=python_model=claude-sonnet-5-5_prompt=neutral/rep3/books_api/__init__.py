"""Book collection REST API (stdlib WSGI + SQLite)."""

from .app import create_app
from .store import BookStore, DuplicateISBN

__all__ = ["create_app", "BookStore", "DuplicateISBN"]
