"""Book collection REST API (standard-library WSGI app + SQLite)."""

from .app import BookApp, create_app
from .db import BookRepository

__all__ = ["BookApp", "BookRepository", "create_app"]
