"""HTTP endpoints for the book collection."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Blueprint, jsonify, request, url_for

from . import repository
from .db import get_db
from .errors import NotFoundError, ValidationError
from .validation import validate_book, validate_book_patch, validate_pagination

bp = Blueprint("books", __name__)

API_VERSION = "1.0.0"


def _json_body() -> Any:
    """Return the parsed JSON body, or fail with a 400.

    ``force=True`` means a client that forgets ``Content-Type: application/json``
    still gets served rather than a 415.
    """
    body = request.get_json(silent=True, force=True)
    if body is None:
        raise ValidationError(
            "Request body must be valid JSON.",
            details={"body": "Send a JSON object such as "
                             '{"title": "...", "author": "..."}.'},
        )
    return body


def _load_book(book_id: int) -> dict[str, Any]:
    book = repository.get_book(get_db(), book_id)
    if book is None:
        raise NotFoundError(f"No book with id {book_id}.")
    return book


@bp.get("/")
def index():
    """Tiny service description, handy when poking at the API by hand."""
    return jsonify(
        {
            "service": "book-collection-api",
            "version": API_VERSION,
            "endpoints": {
                "health": "GET /health",
                "list_books": "GET /books?author=&limit=&offset=",
                "create_book": "POST /books",
                "get_book": "GET /books/<id>",
                "replace_book": "PUT /books/<id>",
                "update_book": "PATCH /books/<id>",
                "delete_book": "DELETE /books/<id>",
            },
        }
    )


@bp.get("/health")
def health():
    """Report liveness plus whether the database actually answers."""
    try:
        books = repository.count_books(get_db())
    except sqlite3.Error as exc:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "version": API_VERSION,
                    "database": "unavailable",
                    "detail": str(exc),
                }
            ),
            503,
        )

    return jsonify(
        {
            "status": "ok",
            "version": API_VERSION,
            "database": "ok",
            "books": books,
        }
    )


@bp.post("/books")
def create_book():
    data = validate_book(_json_body())
    book = repository.create_book(get_db(), data)
    location = url_for("books.get_book", book_id=book["id"])
    return jsonify(book), 201, {"Location": location}


@bp.get("/books")
def list_books():
    author = request.args.get("author")
    if author is not None:
        # A blank ?author= means "no filter" rather than "author is empty".
        author = author.strip() or None
    limit, offset = validate_pagination(request.args)

    conn = get_db()
    books = repository.list_books(conn, author=author, limit=limit, offset=offset)
    total = repository.count_books(conn, author=author)
    return jsonify(books), 200, {"X-Total-Count": str(total)}


@bp.get("/books/<int:book_id>")
def get_book(book_id: int):
    return jsonify(_load_book(book_id))


@bp.put("/books/<int:book_id>")
def replace_book(book_id: int):
    """Full replacement: ``title`` and ``author`` are required, and any omitted
    optional field (``year``, ``isbn``) is cleared."""
    data = validate_book(_json_body())
    book = repository.update_book(get_db(), book_id, data)
    if book is None:
        raise NotFoundError(f"No book with id {book_id}.")
    return jsonify(book)


@bp.patch("/books/<int:book_id>")
def update_book(book_id: int):
    """Partial update: only the supplied fields change."""
    changes = validate_book_patch(_json_body())
    book = repository.update_book(get_db(), book_id, changes)
    if book is None:
        raise NotFoundError(f"No book with id {book_id}.")
    return jsonify(book)


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    if not repository.delete_book(get_db(), book_id):
        raise NotFoundError(f"No book with id {book_id}.")
    return "", 204
