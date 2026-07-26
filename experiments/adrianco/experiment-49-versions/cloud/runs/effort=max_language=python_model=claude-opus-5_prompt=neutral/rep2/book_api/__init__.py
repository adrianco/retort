"""A small REST API for managing a book collection.

The package exposes an application factory, :func:`create_app`, so that the
service can be configured differently for production and for tests.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

from flask import Flask

__version__ = "1.0.0"

#: Database used when ``BOOK_API_DATABASE`` is not set.  ``:memory:`` is also a
#: valid value and gives a private, per-process database.
DEFAULT_DATABASE = "books.db"

#: Upper bound for the ``?limit=`` query parameter of ``GET /books``.
DEFAULT_MAX_PAGE_SIZE = 500

#: Largest accepted request body, in bytes.
DEFAULT_MAX_CONTENT_LENGTH = 1024 * 1024


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def create_app(config: Optional[Mapping[str, Any]] = None) -> Flask:
    """Build and configure the Flask application.

    Args:
        config: Optional mapping merged on top of the environment-derived
            defaults.  Tests typically pass ``{"DATABASE": ":memory:"}``.
    """
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE=os.environ.get("BOOK_API_DATABASE", DEFAULT_DATABASE),
        # Verify the ISBN check digit in addition to its shape (opt-in).
        STRICT_ISBN_CHECKSUM=_env_flag("BOOK_API_STRICT_ISBN", False),
        MAX_PAGE_SIZE=_env_int("BOOK_API_MAX_PAGE_SIZE", DEFAULT_MAX_PAGE_SIZE),
        SQLITE_TIMEOUT=_env_float("BOOK_API_SQLITE_TIMEOUT", 5.0),
        # Refuse oversized bodies before buffering them into memory.
        MAX_CONTENT_LENGTH=_env_int("BOOK_API_MAX_CONTENT_LENGTH", DEFAULT_MAX_CONTENT_LENGTH),
    )
    if config:
        app.config.from_mapping(config)

    # Keep the field order of the serialised models instead of sorting keys,
    # and treat "/books/" as an alias of "/books".
    app.json.sort_keys = False
    app.url_map.strict_slashes = False

    from . import db, errors, routes

    db.init_app(app)
    errors.register_error_handlers(app)
    app.register_blueprint(routes.bp)

    return app


__all__ = ["create_app", "__version__"]
