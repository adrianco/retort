"""HTTP endpoints for the book collection."""

from __future__ import annotations

import sqlite3
from typing import Any, Optional

from flask import Blueprint, Response, abort, jsonify, request, url_for

from . import repository
from .db import get_db
from .validation import (
    validate_book_update,
    validate_new_book,
    validate_positive_int,
)

bp = Blueprint("books", __name__)

MAX_LIMIT = 1000


def _json_body() -> Any:
    """Parse the request body as JSON.

    ``force`` makes the API forgiving about a missing/incorrect ``Content-Type``
    header; ``silent`` turns malformed JSON into ``None``, which the validators
    then report as a proper 400 instead of Flask's default HTML error page.
    """
    return request.get_json(silent=True, force=True)


def _book_or_404(book_id: int) -> dict:
    book = repository.get(get_db(), book_id)
    if book is None:
        abort(404, description=f"Book with id {book_id} was not found")
    return book


@bp.get("/health")
def health() -> Response:
    """Liveness/readiness probe; also checks that SQLite is reachable."""
    try:
        get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:  # pragma: no cover - needs a broken database
        response = jsonify(
            {"status": "error", "database": "unavailable", "error": str(exc)}
        )
        response.status_code = 503
        return response
    return jsonify({"status": "ok", "database": "connected"})


@bp.post("/books")
def create_book() -> Response:
    """Create a book.  Returns 201 with the stored representation."""
    data = validate_new_book(_json_body())
    book = repository.create(get_db(), data)

    response = jsonify(book)
    response.status_code = 201
    response.headers["Location"] = url_for("books.get_book", book_id=book["id"])
    return response


@bp.get("/books")
def list_books() -> Response:
    """List books as a JSON array.

    Query parameters:
      * ``author`` -- exact, case-insensitive filter on the author name
      * ``limit``  -- optional page size (1..1000)
      * ``offset`` -- optional number of rows to skip
    """
    author = (request.args.get("author") or "").strip() or None

    limit: Optional[int] = None
    if "limit" in request.args:
        limit = validate_positive_int(
            "limit", request.args["limit"], minimum=0, maximum=MAX_LIMIT
        )
    offset = 0
    if "offset" in request.args:
        offset = validate_positive_int("offset", request.args["offset"])

    books, total = repository.list_books(
        get_db(), author=author, limit=limit, offset=offset
    )

    response = jsonify(books)
    response.headers["X-Total-Count"] = str(total)
    return response


@bp.get("/books/<int:book_id>")
def get_book(book_id: int) -> Response:
    """Fetch a single book by id."""
    return jsonify(_book_or_404(book_id))


@bp.route("/books/<int:book_id>", methods=["PUT", "PATCH"])
def update_book(book_id: int) -> Response:
    """Update a book.

    Accepts either a complete representation or only the fields to change.
    Sending ``null`` for ``year``/``isbn`` clears them.
    """
    changes = validate_book_update(_json_body())
    book = repository.update(get_db(), book_id, changes)
    if book is None:
        abort(404, description=f"Book with id {book_id} was not found")
    return jsonify(book)


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    """Delete a book.  Returns 204 with an empty body."""
    if not repository.delete(get_db(), book_id):
        abort(404, description=f"Book with id {book_id} was not found")
    return "", 204
