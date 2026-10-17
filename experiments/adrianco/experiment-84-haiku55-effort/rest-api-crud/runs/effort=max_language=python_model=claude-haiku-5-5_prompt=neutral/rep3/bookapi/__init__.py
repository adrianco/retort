"""A REST API for managing a book collection, stored in SQLite."""

import sqlite3

from flask import Flask, jsonify

from . import db
from .books import bp as books_bp
from .errors import register_error_handlers


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(DATABASE=db.default_database_path())
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    register_error_handlers(app)
    app.register_blueprint(books_bp)
    app.add_url_rule("/health", view_func=health)
    return app


def health():
    try:
        db.get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return jsonify(status="error", database="unavailable"), 503
    return jsonify(status="ok", database="ok")
