"""Book collection REST API: a WSGI application backed by SQLite (standard library only)."""

from .app import BookAPI, create_app
from .repository import BookRepository

__version__ = "1.0.0"

__all__ = ["BookAPI", "BookRepository", "__version__", "create_app"]
