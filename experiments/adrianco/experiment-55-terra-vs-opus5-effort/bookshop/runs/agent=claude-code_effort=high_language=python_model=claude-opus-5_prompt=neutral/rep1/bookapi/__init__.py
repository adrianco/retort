"""A small REST API for managing a book collection (Flask + SQLite)."""

from __future__ import annotations

import os

from flask import Flask, jsonify

from . import db
from .routes import bp

__all__ = ["create_app"]

DEFAULT_DATABASE = "books.db"


def create_app(config: dict | None = None) -> Flask:
    """Application factory.

    The database location comes from ``config["DATABASE"]``, else the
    ``BOOKS_DB_PATH`` environment variable, else ``books.db`` in the CWD.
    """
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("BOOKS_DB_PATH", DEFAULT_DATABASE),
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)

    _register_error_handlers(app)
    db.init_app(app)
    app.register_blueprint(bp)
    return app


def _register_error_handlers(app: Flask) -> None:
    """Return JSON (not Flask's HTML pages) for framework-level errors."""

    @app.errorhandler(400)
    def _bad_request(exc):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def _not_found(exc):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def _method_not_allowed(exc):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(415)
    def _unsupported_media_type(exc):
        return jsonify({"error": "Request body must be valid JSON"}), 400

    @app.errorhandler(500)
    def _server_error(exc):
        return jsonify({"error": "Internal server error"}), 500
