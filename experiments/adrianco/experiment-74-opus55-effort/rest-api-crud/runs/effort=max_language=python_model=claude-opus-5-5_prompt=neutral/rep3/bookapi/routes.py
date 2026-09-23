"""HTTP endpoints of the book collection API."""

from __future__ import annotations

import sqlite3
from typing import Any, NoReturn

from flask import Blueprint, abort, current_app, request, url_for
from werkzeug.routing import IntegerConverter, Map

from .db import get_db
from .repository import Book, BookRepository
from .validation import validate_book

bp = Blueprint("books", __name__)

#: Largest value a SQLite INTEGER can hold.
MAX_SQLITE_INTEGER = 2**63 - 1


class BookIdConverter(IntegerConverter):
    """URL converter for book IDs: positive integers that fit in SQLite.

    Anything else fails to match the route and is a 404, instead of an
    OverflowError (and a 500) when the ID reaches the database.
    """

    def __init__(self, url_map: Map) -> None:
        super().__init__(url_map, min=1, max=MAX_SQLITE_INTEGER)


@bp.get("/health")
def health() -> Any:
    try:
        # Read the books table itself: a bare "SELECT 1" never touches the file,
        # so it would pass even if the database were deleted or corrupted.
        get_db().execute("SELECT 1 FROM books LIMIT 1").fetchone()
    except sqlite3.Error:
        current_app.logger.exception("Health check could not read the database")
        return {"status": "unavailable", "database": "error"}, 503
    return {"status": "ok", "database": "ok"}


@bp.post("/books")
def create_book() -> Any:
    book = _books().create(validate_book(_json_object()))
    return book, 201, {"Location": url_for(".get_book", book_id=book["id"])}


@bp.get("/books")
def list_books() -> Any:
    author = request.args.get("author", "").strip()
    return _books().find(author=author or None)


@bp.get("/books/<book_id:book_id>")
def get_book(book_id: int) -> Any:
    return _book_or_404(_books().get(book_id), book_id)


@bp.put("/books/<book_id:book_id>")
def replace_book(book_id: int) -> Any:
    fields = validate_book(_json_object())
    return _book_or_404(_books().replace(book_id, fields), book_id)


@bp.delete("/books/<book_id:book_id>")
def delete_book(book_id: int) -> Any:
    if not _books().delete(book_id):
        _not_found(book_id)
    return "", 204


def _books() -> BookRepository:
    return BookRepository(get_db())


def _book_or_404(book: Book | None, book_id: int) -> Book:
    if book is None:
        _not_found(book_id)
    return book


def _not_found(book_id: int) -> NoReturn:
    abort(404, description=f"Book {book_id} not found")


def _json_object() -> dict[str, Any]:
    """The request body, which must be a JSON object."""
    if not request.is_json:
        abort(415, description="Request body must be JSON (Content-Type: application/json)")
    data = request.get_json(silent=True)  # None when the body is not valid JSON
    if not isinstance(data, dict):
        abort(400, description="Request body must be a JSON object")
    return data
