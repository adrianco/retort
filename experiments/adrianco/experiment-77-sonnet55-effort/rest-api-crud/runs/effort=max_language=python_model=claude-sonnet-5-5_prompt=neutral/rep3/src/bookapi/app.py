"""The WSGI application: routing and request handlers for the book API."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from http import HTTPStatus
from typing import Any, Callable, Iterable, Union

from .repository import DEFAULT_DATABASE, BookRepository
from .validation import ValidationError, validate_book
from .web import HTTPError, Request, Response, json_response

logger = logging.getLogger(__name__)

Handler = Callable[..., Response]

# Ids are positive SQLite integers, written without leading zeros so that a book has
# exactly one URL. At most 19 digits can name one; longer digit strings simply match no
# route (which also keeps them away from ``int()``).
_BOOK_ID = r"(?P<book_id>[1-9][0-9]{0,18})"


class BookApp:
    """WSGI application (PEP 3333) implementing the book collection API."""

    def __init__(self, repository: BookRepository) -> None:
        self.repository = repository
        self._routes: list[tuple[re.Pattern, dict[str, Handler]]] = [
            (re.compile(r"/health/?"), {"GET": self._health}),
            (re.compile(r"/books/?"), {"GET": self._list_books, "POST": self._create_book}),
            (
                re.compile(rf"/books/{_BOOK_ID}/?"),
                {"GET": self._get_book, "PUT": self._update_book, "DELETE": self._delete_book},
            ),
        ]

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
        request = Request(environ)
        try:
            response = self._dispatch(request)
        except HTTPError as exc:
            response = exc.response()
        except ValidationError as exc:
            response = HTTPError(HTTPStatus.BAD_REQUEST, "Validation failed", details=exc.errors).response()
        except Exception:
            logger.exception("Unhandled error while handling %s %s", request.method, request.path)
            response = HTTPError(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error").response()
        if request.method == "HEAD":
            response = response.without_body()
        start_response(response.status_line, response.headers)
        return [response.body]

    def close(self) -> None:
        self.repository.close()

    def _dispatch(self, request: Request) -> Response:
        # HEAD is GET without a response body (RFC 9110 requires servers to support it).
        method = "GET" if request.method == "HEAD" else request.method
        for pattern, handlers in self._routes:
            match = pattern.fullmatch(request.path)
            if match is None:
                continue
            handler = handlers.get(method)
            if handler is None:
                allowed = set(handlers) | ({"HEAD"} if "GET" in handlers else set())
                raise HTTPError(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "Method not allowed",
                    headers=[("Allow", ", ".join(sorted(allowed)))],
                )
            return handler(request, **match.groupdict())
        raise HTTPError(HTTPStatus.NOT_FOUND, "Not found")

    # --- handlers -------------------------------------------------------

    def _health(self, request: Request) -> Response:
        try:
            self.repository.ping()
        except sqlite3.Error:
            logger.exception("Health check failed: database unavailable")
            body = {"status": "unavailable", "error": "Database unavailable"}
            return json_response(HTTPStatus.SERVICE_UNAVAILABLE, body)
        return json_response(HTTPStatus.OK, {"status": "ok"})

    def _list_books(self, request: Request) -> Response:
        books = self.repository.list_books(author=request.query_param("author"))
        return json_response(HTTPStatus.OK, books)

    def _create_book(self, request: Request) -> Response:
        fields = validate_book(request.json_object())
        book = self.repository.create_book(fields)
        location = f"{request.script_name}/books/{book['id']}"
        return json_response(HTTPStatus.CREATED, book, headers=[("Location", location)])

    def _get_book(self, request: Request, book_id: str) -> Response:
        book = self.repository.get_book(int(book_id))
        if book is None:
            raise _book_not_found(book_id)
        return json_response(HTTPStatus.OK, book)

    def _update_book(self, request: Request, book_id: str) -> Response:
        # PUT replaces the whole resource, so it is validated exactly like POST.
        fields = validate_book(request.json_object())
        book = self.repository.update_book(int(book_id), fields)
        if book is None:
            raise _book_not_found(book_id)
        return json_response(HTTPStatus.OK, book)

    def _delete_book(self, request: Request, book_id: str) -> Response:
        if not self.repository.delete_book(int(book_id)):
            raise _book_not_found(book_id)
        return Response(HTTPStatus.NO_CONTENT)


def _book_not_found(book_id: str) -> HTTPError:
    return HTTPError(HTTPStatus.NOT_FOUND, f"Book {book_id} not found")


def create_app(database: Union[str, os.PathLike] = DEFAULT_DATABASE) -> BookApp:
    """Build the WSGI application backed by the SQLite database at ``database``.

    The file (and its parent directories) is created if missing; pass
    ``":memory:"`` for a throw-away in-memory database.
    """
    return BookApp(BookRepository(database))
