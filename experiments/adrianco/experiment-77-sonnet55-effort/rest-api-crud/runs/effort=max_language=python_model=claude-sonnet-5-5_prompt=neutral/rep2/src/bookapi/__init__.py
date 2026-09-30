"""A small REST API for managing a book collection, using only the standard library."""

from .app import BookApp, create_app

__all__ = ["BookApp", "create_app"]
