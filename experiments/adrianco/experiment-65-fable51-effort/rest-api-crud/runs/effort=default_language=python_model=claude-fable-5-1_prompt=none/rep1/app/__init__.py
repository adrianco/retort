"""Book collection REST API (Flask + SQLite)."""
from __future__ import annotations

import os

from flask import Flask, jsonify

from . import db as database
from .routes import bp


def create_app(config: dict | None = None) -> Flask:
    """Application factory.

    config keys:
      DATABASE - path to the SQLite file (":memory:" is NOT supported across
                 requests; use a temp file in tests).
    """
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("BOOKS_DATABASE", "books.db")
    if config:
        app.config.update(config)

    database.init_app(app)
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify(error="method not allowed"), 405

    @app.errorhandler(500)
    def server_error(_err):
        return jsonify(error="internal server error"), 500

    return app
