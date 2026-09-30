"""bookapi: a small JSON REST API for managing a book collection."""

from .app import BookApp, create_app

__all__ = ["BookApp", "create_app"]
