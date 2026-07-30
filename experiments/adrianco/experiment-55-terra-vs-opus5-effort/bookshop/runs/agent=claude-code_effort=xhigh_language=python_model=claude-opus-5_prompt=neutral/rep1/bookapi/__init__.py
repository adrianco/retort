"""A small REST API for managing a book collection.

Flask for HTTP, SQLite for storage, no other runtime dependencies.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from flask import Flask

from . import db, routes
from .errors import register_error_handlers

__all__ = ["create_app"]

DEFAULT_DATABASE = "books.db"


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build the application.

    The database path comes from ``config["DATABASE"]``, else the
    ``BOOK_API_DATABASE`` environment variable, else ``./books.db``.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOK_API_DATABASE", DEFAULT_DATABASE),
    )
    if config:
        app.config.update(config)

    # Keep the field order of our responses instead of alphabetising it.
    if hasattr(app, "json"):
        app.json.sort_keys = False

    db.init_app(app)
    register_error_handlers(app)
    app.register_blueprint(routes.bp)

    db.init_db(app)
    return app
