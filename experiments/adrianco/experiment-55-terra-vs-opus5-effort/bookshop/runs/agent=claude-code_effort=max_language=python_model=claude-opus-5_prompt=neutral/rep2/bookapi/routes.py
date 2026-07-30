"""HTTP layer: URL routing, request parsing and response shaping."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Blueprint, current_app, jsonify, request, url_for

from . import repository
from .db import get_db, ping
from .errors import NotFoundError, ValidationError
from .openapi import build_spec
from .validation import SQLITE_MAX_INT, validate_book_payload, validate_list_query

bp = Blueprint("api", __name__)

BOOK_RULE = "/books/<int:book_id>"


def _json_body() -> Any:
    """Parse the request body as JSON.

    ``force=True`` means a client that forgets ``Content-Type: application/json``
    is still understood; a body that is not valid JSON gets a clear 400 rather
    than Werkzeug's HTML error page.
    """
    body = request.get_json(force=True, silent=True)
    if body is None:
        raise ValidationError("Request body must be valid JSON.")
    return body


def _missing(book_id: int) -> NotFoundError:
    return NotFoundError(f"No book with id {book_id}.")


def _checked_id(book_id: int) -> int:
    """Reject ids SQLite could never have issued.

    The ``int`` converter already excludes negatives and non-digits, but it
    happily yields a Python int wider than SQLite's 64-bit INTEGER, which cannot
    be bound as a parameter.  Screening it here turns what would be an
    OverflowError (500) into the 404 it really is - and doing it in the view
    rather than as ``int(max=...)`` on the rule keeps the answer a 404 for every
    verb, since Werkzeug notes method matches before it runs converters and
    would otherwise report 405 on PUT/PATCH/DELETE.
    """
    if book_id > SQLITE_MAX_INT:
        raise _missing(book_id)
    return book_id


def _load_book(book_id: int) -> dict[str, Any]:
    book = repository.get_book(get_db(), _checked_id(book_id))
    if book is None:
        raise _missing(book_id)
    return book


def _apply_update(book_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    """Update a book or raise 404 - shared by PUT and PATCH."""
    book = repository.update_book(get_db(), _checked_id(book_id), fields)
    if book is None:
        raise _missing(book_id)
    return book


@bp.get("/health")
def health():
    """Liveness/readiness probe: reports whether the database is usable."""
    try:
        stats = ping(get_db())
    except sqlite3.Error as exc:
        current_app.logger.warning("Health check failed: %s", exc)
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "database": "unavailable",
                    "version": current_app.config["API_VERSION"],
                }
            ),
            503,
        )
    return jsonify(
        {
            "status": "ok",
            "database": "ok",
            "books": stats["books"],
            "version": current_app.config["API_VERSION"],
        }
    )


@bp.get("/")
def index():
    """Tiny discovery document so the API root is not a dead end."""
    return jsonify(
        {
            "name": "Book Collection API",
            "version": current_app.config["API_VERSION"],
            "endpoints": {
                "health": url_for("api.health"),
                "books": url_for("api.list_books"),
                "openapi": url_for("api.openapi"),
            },
        }
    )


@bp.get("/openapi.json")
def openapi():
    return jsonify(build_spec(current_app.config["API_VERSION"]))


@bp.get("/books")
def list_books():
    """List books in insertion order, with optional filtering and paging.

    Query parameters: ``author`` (exact, case-insensitive), ``title``
    (substring, case-insensitive), ``year``, ``sort``, ``limit``, ``offset``.
    """
    query = validate_list_query(request.args)
    books, total = repository.list_books(get_db(), **query)
    response = jsonify(books)
    response.headers["X-Total-Count"] = str(total)
    return response


@bp.post("/books")
def create_book():
    fields = validate_book_payload(_json_body())
    book = repository.create_book(get_db(), fields)
    response = jsonify(book)
    response.status_code = 201
    response.headers["Location"] = url_for("api.get_book", book_id=book["id"])
    return response


@bp.get(BOOK_RULE)
def get_book(book_id: int):
    return jsonify(_load_book(book_id))


@bp.put(BOOK_RULE)
def replace_book(book_id: int):
    """Full replacement: omitted optional fields are cleared."""
    fields = validate_book_payload(_json_body())
    return jsonify(_apply_update(book_id, fields))


@bp.patch(BOOK_RULE)
def patch_book(book_id: int):
    """Partial update: only the supplied fields change."""
    fields = validate_book_payload(_json_body(), partial=True)
    return jsonify(_apply_update(book_id, fields))


@bp.delete(BOOK_RULE)
def delete_book(book_id: int):
    if not repository.delete_book(get_db(), _checked_id(book_id)):
        raise _missing(book_id)
    return "", 204
