"""Book collection REST API built on the Python standard library (WSGI + SQLite)."""

from books_api.app import BooksApp, create_app
from books_api.db import BookRepository

__all__ = ["BooksApp", "BookRepository", "create_app"]
