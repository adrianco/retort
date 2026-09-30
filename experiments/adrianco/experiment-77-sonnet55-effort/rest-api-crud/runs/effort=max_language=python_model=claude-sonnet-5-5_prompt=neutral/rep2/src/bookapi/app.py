"""The WSGI application: routing and request handlers for the book API."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import asdict
from http import HTTPStatus
from typing import Callable

from .models import BookInput
from .repository import BookRepository
from .validation import ValidationError, validate_book
from .web import Environ, HTTPError, Request, Response, StartResponse

logger = logging.getLogger(__name__)

DEFAULT_DATABASE = "books.db"

Handler = Callable[..., Response]

# Ids have at most 19 digits: a longer number cannot exist, and the cap keeps int()
# away from absurdly long digit strings. [0-9] rather than \d, which also matches
# non-ASCII digits.
_BOOK_PATH = r"/books/(?P<book_id>[0-9]{1,19})"


class BookApp:
    """WSGI application serving the book collection as a JSON API.

    ==========================  ==========================================
    ``GET /health``             liveness/readiness check
    ``POST /books``             create a book
    ``GET /books``              list books, optionally ``?author=<name>``
    ``GET /books/{id}``         fetch one book
    ``PUT /books/{id}``         replace a book
    ``DELETE /books/{id}``      delete a book
    ==========================  ==========================================
    """

    def __init__(self, repository: BookRepository) -> None:
        self.repository = repository
        self._routes: list[tuple[re.Pattern[str], dict[str, Handler]]] = [
            (re.compile(r"/health"), {"GET": self.health}),
            (re.compile(r"/books"), {"GET": self.list_books, "POST": self.create_book}),
            (
                re.compile(_BOOK_PATH),
                {"GET": self.get_book, "PUT": self.update_book, "DELETE": self.delete_book},
            ),
        ]

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterable[bytes]:
        request = Request(environ)
        try:
            response = self._dispatch(request)
        except HTTPError as exc:
            response = exc.to_response()
        except Exception:
            logger.exception("Unhandled error while handling %s %s", request.method, request.path)
            response = HTTPError(
                HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
            ).to_response()
        return response.send(start_response, head_only=request.method == "HEAD")

    def _dispatch(self, request: Request) -> Response:
        for pattern, handlers in self._routes:
            match = pattern.fullmatch(request.path)
            if match is None:
                continue
            # HEAD is answered by the GET handler; the body is dropped when sending.
            handler = handlers.get("GET" if request.method == "HEAD" else request.method)
            if handler is None:
                allowed = set(handlers) | ({"HEAD"} if "GET" in handlers else set())
                raise HTTPError(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "Method not allowed",
                    headers=[("Allow", ", ".join(sorted(allowed)))],
                )
            return handler(request, **match.groupdict())
        raise HTTPError(HTTPStatus.NOT_FOUND, "Not found")

    # -- handlers ---------------------------------------------------------------

    def health(self, request: Request) -> Response:
        try:
            self.repository.ping()
        except sqlite3.Error:
            logger.exception("Health check failed: database unavailable")
            return Response(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable"})
        return Response(HTTPStatus.OK, {"status": "ok"})

    def list_books(self, request: Request) -> Response:
        books = self.repository.list_books(request.query_param("author"))
        return Response(HTTPStatus.OK, [asdict(book) for book in books])

    def create_book(self, request: Request) -> Response:
        book = self.repository.create(_book_from_body(request))
        location = f"{request.script_name}/books/{book.id}"
        return Response(HTTPStatus.CREATED, asdict(book), headers=[("Location", location)])

    def get_book(self, request: Request, book_id: str) -> Response:
        book = self.repository.get(int(book_id))
        if book is None:
            raise _book_not_found()
        return Response(HTTPStatus.OK, asdict(book))

    def update_book(self, request: Request, book_id: str) -> Response:
        book = self.repository.update(int(book_id), _book_from_body(request))
        if book is None:
            raise _book_not_found()
        return Response(HTTPStatus.OK, asdict(book))

    def delete_book(self, request: Request, book_id: str) -> Response:
        if not self.repository.delete(int(book_id)):
            raise _book_not_found()
        return Response(HTTPStatus.NO_CONTENT)


def create_app(database: str | os.PathLike[str] | None = None) -> BookApp:
    """Open the database (creating it if needed) and build the application.

    Without an argument the path comes from ``$BOOKS_DB`` (if set and not empty), then
    ``books.db``. This is the factory to hand to an external WSGI server.
    """
    if database is None:
        database = os.environ.get("BOOKS_DB") or DEFAULT_DATABASE
    return BookApp(BookRepository(database))


def _book_from_body(request: Request) -> BookInput:
    try:
        return validate_book(request.json_body())
    except ValidationError as exc:
        raise HTTPError(
            HTTPStatus.BAD_REQUEST, f"Validation failed: {exc}", details=exc.errors
        ) from None


def _book_not_found() -> HTTPError:
    return HTTPError(HTTPStatus.NOT_FOUND, "Book not found")
