"""REST API for managing a book collection (Flask + SQLite)."""

import os

from flask import Flask, g, jsonify, request

import db


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload):
    """Validate a create/update payload, returning a normalised dict."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "expected a JSON object"})

    errors = {}
    clean = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str):
            errors[field] = "must be a string"
        elif not value.strip():
            errors[field] = "must not be empty"
        else:
            clean[field] = value.strip()

    year = payload.get("year")
    if year is None:
        clean["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    elif not 0 <= year <= 2200:
        errors["year"] = "must be between 0 and 2200"
    else:
        clean["year"] = year

    isbn = payload.get("isbn")
    if isbn is None:
        clean["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        digits = isbn.replace("-", "").replace(" ", "")
        if digits and len(digits) not in (10, 13):
            errors["isbn"] = "must have 10 or 13 digits"
        else:
            clean["isbn"] = isbn.strip() or None

    if errors:
        raise ValidationError(errors)
    return clean


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", "books.db")

    def get_conn():
        if "conn" not in g:
            g.conn = db.connect(app.config["DATABASE"])
        return g.conn

    @app.teardown_appcontext
    def close_conn(_exc):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    with app.app_context():
        db.init_db(get_conn())

    def json_body():
        payload = request.get_json(silent=True)
        if payload is None:
            raise ValidationError({"body": "a JSON body is required"})
        return payload

    @app.errorhandler(ValidationError)
    def handle_validation(exc):
        return jsonify({"error": "validation failed", "details": exc.errors}), 400

    @app.errorhandler(404)
    def handle_404(_exc):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def handle_405(_exc):
        return jsonify({"error": "method not allowed"}), 405

    @app.get("/health")
    def health():
        get_conn().execute("SELECT 1")
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        book = db.create_book(get_conn(), validate_book(json_body()))
        return jsonify(book), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        return jsonify(db.list_books(get_conn(), author)), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = db.get_book(get_conn(), book_id)
        if book is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(book), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        book = db.update_book(get_conn(), book_id, validate_book(json_body()))
        if book is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(book), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        if not db.delete_book(get_conn(), book_id):
            return jsonify({"error": "book not found"}), 404
        return "", 204

    return app


def __getattr__(name):
    """Build the app on first access to `app.app`, not at import time.

    This keeps merely importing this module (e.g. from tests) from creating a
    database file, while still supporting `flask --app app run` and WSGI
    servers that expect an `app` attribute.
    """
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
