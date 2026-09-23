"""A REST API for managing a book collection, built on Flask and SQLite."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from flask import Flask

from . import db
from .errors import register_error_handlers
from .routes import BookIdConverter, bp

__all__ = ["create_app"]


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build the application; *config* overrides the default settings.

    ``DATABASE`` is the path of the SQLite file. It defaults to the
    ``BOOKS_DB_PATH`` environment variable, or ``books.db`` in the working
    directory, and is created on first start.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        # `or`, not a get() default: an empty path would give every connection
        # its own private temporary database.
        DATABASE=os.environ.get("BOOKS_DB_PATH") or "books.db",
        # A book is a few hundred bytes; refuse (413) anything absurdly large.
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if config:
        app.config.from_mapping(config)
    app.json.sort_keys = False  # keep the natural id, title, author, year, isbn order

    db.init_app(app)
    # Converters are looked up when rules are added, so this must precede the blueprint.
    app.url_map.converters["book_id"] = BookIdConverter
    app.register_blueprint(bp)
    register_error_handlers(app)
    return app
