"""Book collection REST API (Flask + SQLite)."""

import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from . import api, db
from .validation import ValidationError

__all__ = ["create_app"]


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory.

    ``DATABASE`` defaults to ``books.sqlite3`` next to the package, and can be
    overridden with the ``BOOKS_DATABASE`` environment variable or by passing
    ``test_config``.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "BOOKS_DATABASE",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "books.sqlite3"),
        )
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.register_blueprint(api.bp)

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return jsonify({"error": "Validation failed", "details": exc.errors}), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        return jsonify({"error": exc.description}), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):  # pragma: no cover
        app.logger.exception("Unhandled error", exc_info=exc)
        return jsonify({"error": "Internal server error"}), 500

    # Create the schema on startup so the service is usable out of the box.
    with app.app_context():
        db.init_db()

    return app
