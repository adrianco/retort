"""HTTP routes for the book collection API."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Blueprint, jsonify, request, url_for

from . import repository
from .db import get_db
from .errors import NotFoundError, UnsupportedMediaTypeError, ValidationError
from .validation import validate_book_payload

bp = Blueprint("api", __name__)

# Werkzeug's int converter is unsigned but unbounded above, so book_id can be an
# integer too large for SQLite to bind. repository treats those as "no such row",
# which keeps this a 404 across all three verbs. (Capping the converter here
# instead would make Werkzeug answer PUT/DELETE with a misleading 405, because a
# rejected converter still counts the rule's other methods as a path match.)
BOOK_ID = "<int:book_id>"


def _json_body() -> Any:
    """Parse the request body as JSON or raise the right 4xx."""
    if not request.is_json:
        raise UnsupportedMediaTypeError(
            "Content-Type must be application/json; got "
            f"{request.mimetype or 'nothing'}."
        )
    body = request.get_json(silent=True)
    if body is None:
        raise ValidationError("Request body must be valid, non-empty JSON.")
    return body


def _book_or_404(book_id: int) -> dict[str, Any]:
    book = repository.get_book(get_db(), book_id)
    if book is None:
        raise NotFoundError(f"No book with id {book_id}.")
    return book


@bp.get("/health")
def health():
    """Liveness *and* readiness: the DB is actually queried.

    OSError as well as sqlite3.Error, because opening the database may first have
    to create its parent directory -- a read-only mount or a non-directory path
    component fails there, before sqlite is ever reached.
    """
    try:
        get_db().execute("SELECT 1").fetchone()
    except (sqlite3.Error, OSError) as exc:
        return jsonify(status="error", database="unavailable", detail=str(exc)), 503
    return jsonify(status="ok", database="ok")


@bp.post("/books")
def create_book():
    payload = _json_body()
    data = validate_book_payload(payload)
    book = repository.create_book(get_db(), data)
    return (
        jsonify(book),
        201,
        {"Location": url_for("api.get_book", book_id=book["id"])},
    )


@bp.get("/books")
def list_books():
    # A blank ?author= is treated as "no filter" rather than "author equal to
    # the empty string", which no book can have.
    author = (request.args.get("author") or "").strip() or None
    return jsonify(repository.list_books(get_db(), author=author))


@bp.get(f"/books/{BOOK_ID}")
def get_book(book_id: int):
    return jsonify(_book_or_404(book_id))


@bp.put(f"/books/{BOOK_ID}")
def replace_book(book_id: int):
    payload = _json_body()
    data = validate_book_payload(payload, expected_id=book_id)
    book = repository.replace_book(get_db(), book_id, data)
    if book is None:
        raise NotFoundError(f"No book with id {book_id}.")
    return jsonify(book)


@bp.delete(f"/books/{BOOK_ID}")
def delete_book(book_id: int):
    if not repository.delete_book(get_db(), book_id):
        raise NotFoundError(f"No book with id {book_id}.")
    return "", 204
