"""The book collection WSGI application: routing and request handlers."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from collections.abc import Callable, Iterable
from typing import Any

from .models import BookData
from .repository import DEFAULT_DATABASE, BookRepository
from .validation import ValidationError, validate_book
from .web import HTTPError, Request, Response, StartResponse

logger = logging.getLogger(__name__)

Handler = Callable[..., Response]

# Canonical ids only: no sign, no leading zeros, at most 19 digits (the width of an int64).
_ID_PATTERN = re.compile(r"[1-9][0-9]{0,18}")


def _book_not_found() -> HTTPError:
    return HTTPError(404, "Book not found")


def _parse_id(raw: str) -> int:
    if _ID_PATTERN.fullmatch(raw) is None:
        raise _book_not_found()  # such an id can never exist
    return int(raw)


def _allowed_methods(handlers: dict[str, Handler]) -> str:
    methods = set(handlers) | {"OPTIONS"}
    if "GET" in handlers:
        methods.add("HEAD")
    return ", ".join(sorted(methods))


def _validated_body(request: Request) -> BookData:
    try:
        return validate_book(request.json_object())
    except ValidationError as exc:
        raise HTTPError(400, "Validation failed", details=exc.errors) from None


class BookAPI:
    """WSGI application implementing the book collection REST API.

    Every response, including errors, is JSON. Anything unexpected is logged and reported
    as a generic 500 so internals never leak to clients.
    """

    def __init__(self, repository: BookRepository) -> None:
        self.repository = repository
        self._routes: list[tuple[re.Pattern[str], dict[str, Handler]]] = [
            (re.compile(r"/health"), {"GET": self._health}),
            (re.compile(r"/books"), {"GET": self._list_books, "POST": self._create_book}),
            (
                re.compile(r"/books/(?P<book_id>[^/]+)"),
                {"GET": self._get_book, "PUT": self._update_book, "DELETE": self._delete_book},
            ),
        ]

    def __call__(self, environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        request = Request(environ)
        try:
            response = self._dispatch(request)
        except HTTPError as exc:
            response = exc.to_response()
        except Exception:
            # %r keeps a hostile, URL-decoded path (say, one containing newlines) on one log line.
            logger.exception("Unhandled error while handling %s %r", request.method, request.path)
            response = HTTPError(500, "Internal server error").to_response()
        return response.send(start_response, head_only=request.method == "HEAD")

    def _dispatch(self, request: Request) -> Response:
        for pattern, handlers in self._routes:
            match = pattern.fullmatch(request.path)
            if match is None:
                continue
            allow = ("Allow", _allowed_methods(handlers))
            if request.method == "OPTIONS":
                return Response(204, headers=[allow])
            handler = handlers.get("GET" if request.method == "HEAD" else request.method)
            if handler is None:
                raise HTTPError(405, "Method not allowed", headers=[allow])
            return handler(request, **match.groupdict())
        raise HTTPError(404, "Not found")

    # --- handlers -----------------------------------------------------------------------

    def _health(self, request: Request) -> Response:
        try:
            self.repository.ping()
        except sqlite3.Error:
            logger.exception("Health check failed: database unavailable")
            return Response(503, {"status": "unavailable", "error": "Database unavailable"})
        return Response(200, {"status": "ok"})

    def _list_books(self, request: Request) -> Response:
        authors = request.query.get("author", [])
        if len(authors) > 1:
            raise HTTPError(400, "Query parameter 'author' may be given only once")
        author = authors[0].strip() if authors else ""
        books = self.repository.list_books(author or None)  # a blank filter means no filter
        return Response(200, [book.to_dict() for book in books])

    def _create_book(self, request: Request) -> Response:
        book = self.repository.create(_validated_body(request))
        return Response(201, book.to_dict(), headers=[("Location", f"/books/{book.id}")])

    def _get_book(self, request: Request, book_id: str) -> Response:
        book = self.repository.get(_parse_id(book_id))
        if book is None:
            raise _book_not_found()
        return Response(200, book.to_dict())

    def _update_book(self, request: Request, book_id: str) -> Response:
        parsed_id = _parse_id(book_id)
        book = self.repository.update(parsed_id, _validated_body(request))
        if book is None:
            raise _book_not_found()
        return Response(200, book.to_dict())

    def _delete_book(self, request: Request, book_id: str) -> Response:
        if not self.repository.delete(_parse_id(book_id)):
            raise _book_not_found()
        return Response(204)


def create_app(database: str | os.PathLike[str] | None = None) -> BookAPI:
    """Application factory, e.g. ``gunicorn 'bookapi:create_app()'``.

    The database defaults to ``$BOOKS_DB``, or ``books.db`` in the working directory.
    """
    database = database or os.environ.get("BOOKS_DB") or DEFAULT_DATABASE
    return BookAPI(BookRepository(database))
