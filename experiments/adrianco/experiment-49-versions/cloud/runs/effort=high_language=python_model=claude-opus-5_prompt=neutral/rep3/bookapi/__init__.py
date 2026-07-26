"""A small REST service for managing a book collection."""

from __future__ import annotations

import os

from flask import Flask

from .db import close_db, init_db
from .errors import register_error_handlers
from .routes import bp

DEFAULT_DATABASE = "books.db"


def create_app(database: str | None = None) -> Flask:
    """Build the application.

    ``database`` defaults to the ``BOOKS_DB`` environment variable, then to
    ``books.db`` in the working directory.
    """
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", DEFAULT_DATABASE)
    # Keep JSON key order as written rather than sorting it alphabetically.
    app.json.sort_keys = False

    app.teardown_appcontext(close_db)
    register_error_handlers(app)
    app.register_blueprint(bp)

    init_db(app)
    return app
