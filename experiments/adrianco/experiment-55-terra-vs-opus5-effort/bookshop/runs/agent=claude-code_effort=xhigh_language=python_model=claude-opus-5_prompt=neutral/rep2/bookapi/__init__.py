"""A small REST API for managing a book collection, backed by SQLite."""

from __future__ import annotations

import os

from flask import Flask

from .db import close_db, init_db
from .errors import register_error_handlers
from .routes import bp

__all__ = ["create_app"]


def create_app(config: dict | None = None) -> Flask:
    """Build and configure the application.

    The database file defaults to ``books.db`` in the working directory and can
    be overridden with the ``BOOKAPI_DATABASE`` environment variable or by
    passing ``{"DATABASE": ...}``.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKAPI_DATABASE", "books.db"),
        DATABASE_TIMEOUT=float(os.environ.get("BOOKAPI_DATABASE_TIMEOUT", "10")),
    )
    if config:
        app.config.from_mapping(config)

    # Keep the field order used in responses (id, title, author, year, isbn).
    app.json.sort_keys = False

    init_db(app)
    app.teardown_appcontext(close_db)
    register_error_handlers(app)
    app.register_blueprint(bp)
    return app
