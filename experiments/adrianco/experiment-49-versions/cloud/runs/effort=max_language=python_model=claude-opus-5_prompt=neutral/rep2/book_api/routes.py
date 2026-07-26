"""HTTP layer: every endpoint of the book collection API."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, url_for

from . import __version__
from .db import get_db
from .errors import NotFoundError, ValidationError
from .repository import BookRepository
from .utils import utcnow_iso
from .validators import parse_book_payload, parse_list_query

bp = Blueprint("books", __name__)


def _repository() -> BookRepository:
    return BookRepository(get_db())


def _json_body() -> Any:
    """Decode the request body as JSON.

    ``force=True`` makes the API forgiving about a missing or wrong
    ``Content-Type`` header; a body that is not valid JSON is still rejected.
    """
    body = request.get_json(silent=True, force=True)
    if body is None:
        raise ValidationError(
            "The request body must be a JSON object.",
            details={"body": "The body is missing or is not valid JSON."},
        )
    return body


def _book_not_found(book_id: int) -> NotFoundError:
    return NotFoundError("No book exists with id {}.".format(book_id))


@bp.get("/")
def index() -> Response:
    """A small, self-describing index of the API."""
    return jsonify(
        {
            "service": "book-api",
            "version": __version__,
            "endpoints": {
                "health": "GET /health",
                "list_books": "GET /books?author=&year=&q=&sort=&limit=&offset=",
                "create_book": "POST /books",
                "get_book": "GET /books/<id>",
                "replace_book": "PUT /books/<id>",
                "update_book": "PATCH /books/<id>",
                "delete_book": "DELETE /books/<id>",
            },
        }
    )


@bp.get("/health")
def health() -> Response:
    """Report service and database health."""
    payload = {
        "status": "ok",
        "version": __version__,
        "database": "ok",
        "books": 0,
        "time": utcnow_iso(),
    }
    try:
        payload["books"] = _repository().total()
    except sqlite3.Error as exc:
        # Log the driver message; do not hand it to an unauthenticated client.
        current_app.logger.warning("Health check could not reach the database: %s", exc)
        payload.update(status="unavailable", database="error")
        response = jsonify(payload)
        response.status_code = 503
        return response
    return jsonify(payload)


@bp.post("/books")
def create_book() -> Response:
    """Create a book.  ``title`` and ``author`` are required."""
    fields = parse_book_payload(
        _json_body(),
        strict_isbn_checksum=current_app.config["STRICT_ISBN_CHECKSUM"],
    )
    book = _repository().create(fields)
    response = jsonify(book.to_dict())
    response.status_code = 201
    response.headers["Location"] = url_for(".get_book", book_id=book.id)
    return response


@bp.get("/books")
def list_books() -> Response:
    """List books as a JSON array, optionally filtered, sorted and paginated."""
    criteria = parse_list_query(request.args, max_limit=current_app.config["MAX_PAGE_SIZE"])
    repository = _repository()
    books = repository.list(**criteria)
    total = repository.count(
        author=criteria["author"], year=criteria["year"], query=criteria["query"]
    )

    response = jsonify([book.to_dict() for book in books])
    # Pagination metadata travels in headers so the body stays a plain array.
    response.headers["X-Total-Count"] = str(total)
    if criteria["limit"] is not None:
        response.headers["X-Limit"] = str(criteria["limit"])
    if criteria["offset"]:
        response.headers["X-Offset"] = str(criteria["offset"])
    return response


@bp.get("/books/<int:book_id>")
def get_book(book_id: int) -> Response:
    """Fetch a single book by id."""
    book = _repository().get(book_id)
    if book is None:
        raise _book_not_found(book_id)
    return jsonify(book.to_dict())


@bp.put("/books/<int:book_id>")
def replace_book(book_id: int) -> Response:
    """Replace a book.  Omitted optional fields are cleared."""
    fields = parse_book_payload(
        _json_body(),
        strict_isbn_checksum=current_app.config["STRICT_ISBN_CHECKSUM"],
    )
    book = _repository().replace(book_id, fields)
    if book is None:
        raise _book_not_found(book_id)
    return jsonify(book.to_dict())


@bp.patch("/books/<int:book_id>")
def update_book(book_id: int) -> Response:
    """Update only the supplied fields of a book."""
    fields = parse_book_payload(
        _json_body(),
        partial=True,
        strict_isbn_checksum=current_app.config["STRICT_ISBN_CHECKSUM"],
    )
    book = _repository().update(book_id, fields)
    if book is None:
        raise _book_not_found(book_id)
    return jsonify(book.to_dict())


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int) -> Response:
    """Delete a book."""
    if not _repository().delete(book_id):
        raise _book_not_found(book_id)
    response = Response(status=204)
    # A 204 carries no body, so it should not advertise a content type either.
    response.headers.pop("Content-Type", None)
    return response
