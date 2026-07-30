"""HTTP endpoints for the book collection."""

from __future__ import annotations

import sqlite3

from flask import Blueprint, abort, current_app, jsonify, request, url_for

from . import store
from .db import get_db
from .validation import validate_book

bp = Blueprint("books", __name__)


@bp.get("/health")
def health():
    """Report service status, including whether the database answers a query."""
    try:
        get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error:
        current_app.logger.exception("Health check could not reach the database")
        return jsonify({"status": "unhealthy", "database": "unavailable"}), 503
    return jsonify({"status": "ok", "database": "ok"}), 200


@bp.post("/books")
def create_book():
    fields = validate_book(_payload())
    book = store.create_book(get_db(), fields)
    location = url_for("books.get_book", book_id=book["id"])
    return jsonify(book), 201, {"Location": location}


@bp.get("/books")
def list_books():
    books = store.list_books(get_db(), author=request.args.get("author"))
    return jsonify(books), 200


@bp.get("/books/<int:book_id>")
def get_book(book_id: int):
    book = store.get_book(get_db(), book_id)
    if book is None:
        _not_found(book_id)
    return jsonify(book), 200


@bp.put("/books/<int:book_id>")
def replace_book(book_id: int):
    """Full replacement: title and author are required, omitted fields cleared."""
    fields = validate_book(_payload())
    book = store.update_book(get_db(), book_id, fields)
    if book is None:
        _not_found(book_id)
    return jsonify(book), 200


@bp.patch("/books/<int:book_id>")
def patch_book(book_id: int):
    """Partial update: only the supplied fields change."""
    fields = validate_book(_payload(), partial=True)
    book = store.update_book(get_db(), book_id, fields)
    if book is None:
        _not_found(book_id)
    return jsonify(book), 200


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    if not store.delete_book(get_db(), book_id):
        _not_found(book_id)
    return "", 204


def _payload() -> object:
    """Parse the request body as JSON.

    ``force`` ignores a missing or wrong Content-Type and ``silent`` turns a
    parse failure into ``None``, which validate_book() reports as a 400 rather
    than Flask's stock HTML error page.
    """
    return request.get_json(force=True, silent=True)


def _not_found(book_id: int) -> None:
    abort(404, description=f"Book {book_id} not found")
