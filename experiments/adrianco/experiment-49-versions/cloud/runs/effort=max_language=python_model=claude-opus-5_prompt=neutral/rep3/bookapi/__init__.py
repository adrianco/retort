"""A small REST service for managing a book collection.

Built with Flask and the standard library's ``sqlite3`` module, using the
application-factory pattern so tests can spin up an isolated instance pointed
at a throwaway database.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from flask import Flask

from . import db, errors, routes

__all__ = ["create_app"]

#: Request bodies larger than this are rejected with 413 before being parsed.
MAX_CONTENT_LENGTH = 256 * 1024


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build and configure the application.

    Args:
        config: Optional overrides applied after the defaults; tests use this
            to point ``DATABASE`` at a temporary file.
    """
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DB_PATH")
        or os.path.join(app.instance_path, "books.db"),
        DATABASE_TIMEOUT=float(os.environ.get("BOOKS_DB_TIMEOUT", "5.0")),
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    )
    if config:
        app.config.from_mapping(config)

    # Preserve the field order defined in the routes rather than alphabetising.
    app.json.sort_keys = False

    db.init_app(app)
    errors.register_error_handlers(app)
    app.register_blueprint(routes.bp)

    return app
