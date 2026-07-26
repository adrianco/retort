"""Book collection REST API.

A small Flask application backed by SQLite.  Use :func:`create_app` to build
an application instance; the factory pattern keeps the app configurable so the
test-suite can point each test at a throwaway database file.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

from flask import Flask

from . import db, errors
from .routes import bp as books_bp

__all__ = ["create_app"]

#: Location of the SQLite file when nothing else is configured.
DEFAULT_DATABASE = "books.db"


def create_app(config: Optional[Mapping[str, Any]] = None) -> Flask:
    """Build and configure the Flask application.

    :param config: optional overrides applied on top of the defaults, e.g.
        ``{"DATABASE": "/tmp/test.db", "TESTING": True}``.
    """
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DB_PATH", DEFAULT_DATABASE),
        TESTING=False,
    )
    if config:
        app.config.from_mapping(config)

    # ``/books/`` should behave exactly like ``/books``.  This has to happen
    # before any rules are registered, because a rule inherits the map default
    # at the time it is bound.
    app.url_map.strict_slashes = False

    # Preserve the field order we build responses in rather than sorting keys.
    if hasattr(app, "json"):  # Flask >= 2.2
        app.json.sort_keys = False

    db.init_app(app)
    errors.register_error_handlers(app)
    app.register_blueprint(books_bp)

    return app
