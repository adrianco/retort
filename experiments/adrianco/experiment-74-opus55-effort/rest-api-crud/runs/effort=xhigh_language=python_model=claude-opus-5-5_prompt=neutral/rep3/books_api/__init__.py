"""Book collection REST API backed by SQLite, built on the standard library."""

from __future__ import annotations

import os
from pathlib import Path

from .app import BookAPI
from .storage import BookRepository

__all__ = ["BookAPI", "BookRepository", "create_app"]


def create_app(database: str | Path | None = None) -> BookAPI:
    """Build the WSGI app, e.g. ``gunicorn 'books_api:create_app()'``.

    The database path defaults to $BOOKS_API_DB, then ``books.db``.
    """
    if database is None:
        database = os.environ.get("BOOKS_API_DB", "books.db")
    return BookAPI(BookRepository(database))
