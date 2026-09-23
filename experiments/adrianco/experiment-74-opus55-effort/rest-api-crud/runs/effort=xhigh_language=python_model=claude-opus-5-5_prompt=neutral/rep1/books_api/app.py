"""WSGI application exposing the book collection as a JSON REST API.

Routes:

    GET    /health       service and database health
    GET    /books        list books (optional ?author= filter)
    POST   /books        create a book
    GET    /books/{id}   fetch one book
    PUT    /books/{id}   replace a book
    DELETE /books/{id}   delete a book

Every response body is JSON, except ``204 No Content``. Errors look like
``{"error": "<message>"}``; validation errors add ``"details"`` mapping each
invalid field to a message.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable, Iterable
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from .models import BookData
from .repository import BookRepository
from .validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024

StartResponse = Callable[..., Any]
Headers = list[tuple[str, str]]


class HTTPError(Exception):
    """An error that maps directly to an HTTP error response."""

    def __init__(
        self,
        status: HTTPStatus,
        message: str,
        details: dict[str, str] | None = None,
        headers: Headers | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []


class Response:
    def __init__(self, status: HTTPStatus, payload: Any = None, headers: Headers | None = None) -> None:
        self.status = status
        self.headers = list(headers or [])
        if status == HTTPStatus.NO_CONTENT:
            # RFC 9110: a 204 response carries neither content nor Content-Length.
            self.body = b""
        else:
            self.body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.headers.append(("Content-Type", "application/json"))
            self.headers.append(("Content-Length", str(len(self.body))))


class Request:
    def __init__(self, environ: dict[str, Any], max_body_bytes: int) -> None:
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO") or "/"
        # Treat "/books/" like "/books".
        self.path = path.rstrip("/") or "/"
        self.query = parse_qs(environ.get("QUERY_STRING", ""))
        self.script_name = environ.get("SCRIPT_NAME", "")
        self._max_body_bytes = max_body_bytes

    def query_param(self, name: str) -> str | None:
        values = self.query.get(name)
        return values[0] if values else None

    def json(self) -> Any:
        """Read and decode the JSON request body."""
        raw_length = (self.environ.get("CONTENT_LENGTH") or "").strip()
        try:
            length = int(raw_length) if raw_length else 0
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header") from None
        if length < 0:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
        if length > self._max_body_bytes:
            raise HTTPError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                f"Request body must not exceed {self._max_body_bytes} bytes",
            )
        body = self.environ["wsgi.input"].read(length) if length else b""
        if not body.strip():
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")
        try:
            return json.loads(body)
        except (ValueError, RecursionError) as exc:  # JSONDecodeError and UnicodeDecodeError are ValueErrors
            raise HTTPError(HTTPStatus.BAD_REQUEST, f"Malformed JSON body: {exc}") from None


Handler = Callable[[Request, dict[str, str]], Response]


class BooksApp:
    """The WSGI callable. Create one per repository."""

    def __init__(self, repository: BookRepository, max_body_bytes: int = MAX_BODY_BYTES) -> None:
        self.repository = repository
        self.max_body_bytes = max_body_bytes
        self._routes: list[tuple[re.Pattern[str], dict[str, Handler]]] = [
            (re.compile(r"/health"), {"GET": self.health}),
            (re.compile(r"/books"), {"GET": self.list_books, "POST": self.create_book}),
            (
                re.compile(r"/books/(?P<book_id>[0-9]{1,19})"),
                {"GET": self.get_book, "PUT": self.update_book, "DELETE": self.delete_book},
            ),
        ]

    def __call__(self, environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        request = Request(environ, self.max_body_bytes)
        try:
            response = self._dispatch(request)
        except HTTPError as exc:
            payload: dict[str, Any] = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
            response = Response(exc.status, payload, exc.headers)
        except Exception:
            logger.exception("Unhandled error processing %s %s", request.method, request.path)
            response = Response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})

        status = f"{response.status.value} {response.status.phrase}"
        start_response(status, response.headers)
        # HEAD gets the GET headers (including Content-Length) without a body.
        if request.method == "HEAD" or not response.body:
            return []
        return [response.body]

    def _dispatch(self, request: Request) -> Response:
        for pattern, handlers in self._routes:
            match = pattern.fullmatch(request.path)
            if match is None:
                continue
            method = "GET" if request.method == "HEAD" else request.method
            handler = handlers.get(method)
            if handler is None:
                allowed = sorted({*handlers, "HEAD"} if "GET" in handlers else handlers)
                raise HTTPError(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    f"Method {request.method} not allowed on {request.path}",
                    headers=[("Allow", ", ".join(allowed))],
                )
            return handler(request, match.groupdict())
        raise HTTPError(HTTPStatus.NOT_FOUND, f"No resource at {request.path}")

    # -- handlers -----------------------------------------------------------

    def health(self, request: Request, params: dict[str, str]) -> Response:
        if self.repository.ping():
            return Response(HTTPStatus.OK, {"status": "ok", "database": "ok"})
        return Response(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "database": "unavailable"})

    def list_books(self, request: Request, params: dict[str, str]) -> Response:
        author = (request.query_param("author") or "").strip() or None
        books = self.repository.list_books(author=author)
        return Response(HTTPStatus.OK, [book.to_dict() for book in books])

    def create_book(self, request: Request, params: dict[str, str]) -> Response:
        data = _validated(request.json())
        book = self.repository.create(data)
        location = f"{request.script_name}/books/{book.id}"
        return Response(HTTPStatus.CREATED, book.to_dict(), [("Location", location)])

    def get_book(self, request: Request, params: dict[str, str]) -> Response:
        book_id = int(params["book_id"])
        book = self.repository.get(book_id)
        if book is None:
            raise _book_not_found(book_id)
        return Response(HTTPStatus.OK, book.to_dict())

    def update_book(self, request: Request, params: dict[str, str]) -> Response:
        book_id = int(params["book_id"])
        data = _validated(request.json())
        book = self.repository.update(book_id, data)
        if book is None:
            raise _book_not_found(book_id)
        return Response(HTTPStatus.OK, book.to_dict())

    def delete_book(self, request: Request, params: dict[str, str]) -> Response:
        book_id = int(params["book_id"])
        if not self.repository.delete(book_id):
            raise _book_not_found(book_id)
        return Response(HTTPStatus.NO_CONTENT)


def _validated(payload: Any) -> BookData:
    try:
        return validate_book(payload)
    except ValidationError as exc:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Validation failed", details=exc.errors) from None


def _book_not_found(book_id: int) -> HTTPError:
    return HTTPError(HTTPStatus.NOT_FOUND, f"Book {book_id} not found")


def create_app(database: str | os.PathLike[str] | None = None) -> BooksApp:
    """Build the WSGI app backed by the SQLite database at ``database``.

    Defaults to the ``BOOKS_API_DB`` environment variable, then ``books.db``.
    """
    if database is None:
        database = os.environ.get("BOOKS_API_DB", "books.db")
    return BooksApp(BookRepository(database))
