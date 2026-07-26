"""HTTP endpoints for the book collection service."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Blueprint, Response, jsonify, request, url_for

from . import db, repository, validation
from .errors import NotFoundError, ValidationError

bp = Blueprint("api", __name__)


def _json_body() -> Any:
    """Return the decoded JSON body, or raise a 400.

    ``force=True`` parses the body even when the client forgot to send a
    ``Content-Type: application/json`` header, which is a common curl mistake
    and not worth failing over.
    """
    payload = request.get_json(silent=True, force=True)
    if payload is None:
        raise ValidationError("Request body must be valid JSON.")
    return payload


def _require_book(book: dict[str, Any] | None, book_id: int) -> dict[str, Any]:
    if book is None:
        raise NotFoundError(f"No book exists with id {book_id}.")
    return book


@bp.get("/health")
def health() -> tuple[Response, int]:
    """Report service liveness, including a real round-trip to the database."""
    try:
        db.get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return jsonify(status="error", database="unavailable"), 503
    return jsonify(status="ok", database="ok"), 200


@bp.post("/books")
def create_book() -> Response:
    """Create a book. Responds 201 with the created resource."""
    data = validation.parse_book(_json_body())
    book = repository.create_book(db.get_db(), data)

    response = jsonify(book)
    response.status_code = 201
    response.headers["Location"] = url_for(".get_book", book_id=book["id"])
    return response


@bp.get("/books")
def list_books() -> tuple[Response, int]:
    """List books, optionally filtered with ``?author=``.

    The filter is an exact, case-insensitive match. A blank value is treated as
    no filter at all.
    """
    author = request.args.get("author")
    if author is not None:
        author = author.strip() or None
    books = repository.list_books(db.get_db(), author)
    return jsonify(books), 200


@bp.get("/books/<int:book_id>")
def get_book(book_id: int) -> tuple[Response, int]:
    """Fetch a single book by id."""
    book = _require_book(repository.get_book(db.get_db(), book_id), book_id)
    return jsonify(book), 200


@bp.put("/books/<int:book_id>")
def replace_book(book_id: int) -> tuple[Response, int]:
    """Replace a book (PUT semantics).

    The body describes the complete resource: ``title`` and ``author`` are
    required, and any omitted optional field is cleared.
    """
    data = validation.parse_book(_json_body())
    book = repository.replace_book(db.get_db(), book_id, data)
    return jsonify(_require_book(book, book_id)), 200


@bp.patch("/books/<int:book_id>")
def update_book(book_id: int) -> tuple[Response, int]:
    """Update only the supplied fields of a book (PATCH semantics)."""
    changes = validation.parse_book(_json_body(), partial=True)
    book = repository.update_book(db.get_db(), book_id, changes)
    return jsonify(_require_book(book, book_id)), 200


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int) -> tuple[str, int]:
    """Delete a book. Responds 204 with an empty body."""
    if not repository.delete_book(db.get_db(), book_id):
        raise NotFoundError(f"No book exists with id {book_id}.")
    return "", 204
