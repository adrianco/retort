"""A small REST API for a book collection, backed by SQLite.

Create an application with :func:`create_app`; see ``README.md`` for the
endpoint contract.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from flask import Flask

from .db import close_db, init_db
from .errors import register_error_handlers
from .routes import bp

__all__ = ["create_app"]

DEFAULT_DATABASE = "books.db"

# A book payload is a few hundred bytes; refuse anything absurd with a 413
# rather than buffering it.
MAX_CONTENT_LENGTH = 64 * 1024


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build a configured application.

    Args:
        config: overrides applied after the defaults. ``DATABASE`` is the
            SQLite file path; it defaults to ``$BOOKS_DB_PATH`` or ``books.db``
            in the working directory.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DB_PATH", DEFAULT_DATABASE),
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    )
    if config:
        app.config.from_mapping(config)

    # Keep the field order from the code instead of alphabetising it.
    app.json.sort_keys = False
    # Accept /books/ as well as /books.
    app.url_map.strict_slashes = False

    app.teardown_appcontext(close_db)
    register_error_handlers(app)
    app.register_blueprint(bp)

    init_db(app)
    return app
