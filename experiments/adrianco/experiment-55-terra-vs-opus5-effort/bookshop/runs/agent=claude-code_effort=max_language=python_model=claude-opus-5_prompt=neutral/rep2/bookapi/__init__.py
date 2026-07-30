"""Book Collection API - a small Flask + SQLite REST service.

Use :func:`create_app` to build an application instance::

    from bookapi import create_app
    app = create_app()
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from flask import Flask

from . import db
from .errors import register_error_handlers
from .routes import bp

__version__ = "1.0.0"
__all__ = ["__version__", "create_app"]

#: Environment variable that overrides where the SQLite file lives.
DATABASE_ENV_VAR = "BOOKS_DB_PATH"


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Build and configure an application instance.

    :param config: overrides applied on top of the defaults; ``DATABASE`` is the
        interesting one and accepts either a file path or ``":memory:"``.
    """
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        DATABASE=os.environ.get(DATABASE_ENV_VAR)
        or os.path.join(app.instance_path, "books.db"),
        API_VERSION=__version__,
    )
    if config:
        app.config.update(config)

    # Preserve the field order defined in the repository rather than
    # alphabetising every JSON object.
    app.json.sort_keys = False

    register_error_handlers(app)
    db.init_app(app)
    app.register_blueprint(bp)

    return app
