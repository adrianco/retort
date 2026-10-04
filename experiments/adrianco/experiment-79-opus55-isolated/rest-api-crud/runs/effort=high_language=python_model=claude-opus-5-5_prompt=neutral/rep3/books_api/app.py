"""WSGI application exposing the books REST API."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any, Callable, Iterable, Optional
from urllib.parse import parse_qs

from .db import BookRepository
from .validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024

_STATUS_TEXT = {
    200: "200 OK",
    201: "201 Created",
    204: "204 No Content",
    400: "400 Bad Request",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    413: "413 Content Too Large",
    500: "500 Internal Server Error",
    503: "503 Service Unavailable",
}

_BOOK_PATH = re.compile(r"^/books/([^/]+)$")
_BOOK_ID = re.compile(r"^[0-9]+$")

Headers = list[tuple[str, str]]
Response = tuple[int, Any, Headers]


class HTTPError(Exception):
    """An error that maps directly onto a JSON error response."""

    def __init__(
        self,
        status: int,
        message: str,
        details: Optional[dict[str, str]] = None,
        headers: Optional[Headers] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []

    def body(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.message}
        if self.details:
            body["details"] = self.details
        return body


class BooksApp:
    """WSGI callable routing requests to a :class:`BookRepository`."""

    def __init__(self, repository: BookRepository) -> None:
        self.repository = repository

    def __call__(
        self, environ: dict[str, Any], start_response: Callable
    ) -> Iterable[bytes]:
        try:
            status, payload, headers = self._dispatch(environ)
        except HTTPError as exc:
            status, payload, headers = exc.status, exc.body(), exc.headers
        except Exception:
            logger.exception("Unhandled error while processing request")
            status, payload, headers = 500, {"error": "Internal server error"}, []

        if payload is None:
            body = b""
        else:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers = [("Content-Type", "application/json; charset=utf-8"), *headers]
        headers = [*headers, ("Content-Length", str(len(body)))]
        start_response(_STATUS_TEXT[status], headers)
        return [body]

    # -- routing ---------------------------------------------------------

    def _dispatch(self, environ: dict[str, Any]) -> Response:
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            return self._route(method, {"GET": self._health}, environ)
        if path == "/books":
            return self._route(
                method, {"GET": self._list_books, "POST": self._create_book}, environ
            )
        match = _BOOK_PATH.match(path)
        if match:
            handlers = {
                "GET": self._get_book,
                "PUT": self._update_book,
                "DELETE": self._delete_book,
            }
            return self._route(method, handlers, environ, match.group(1))
        raise HTTPError(404, "Resource not found")

    @staticmethod
    def _route(
        method: str, handlers: dict[str, Callable], environ: dict[str, Any], *args: str
    ) -> Response:
        handler = handlers.get(method)
        if handler is None:
            allowed = ", ".join(sorted(handlers))
            raise HTTPError(
                405, f"Method {method} not allowed", headers=[("Allow", allowed)]
            )
        return handler(environ, *args)

    # -- handlers --------------------------------------------------------

    def _health(self, environ: dict[str, Any]) -> Response:
        try:
            self.repository.ping()
        except sqlite3.Error:
            logger.exception("Health check failed")
            raise HTTPError(503, "Database unavailable") from None
        return 200, {"status": "ok"}, []

    def _list_books(self, environ: dict[str, Any]) -> Response:
        query = parse_qs(environ.get("QUERY_STRING", ""))
        author = query["author"][0].strip() if "author" in query else None
        return 200, self.repository.list_books(author=author or None), []

    def _create_book(self, environ: dict[str, Any]) -> Response:
        fields = _validated_book(environ)
        book = self.repository.create(fields)
        return 201, book, [("Location", f"/books/{book['id']}")]

    def _get_book(self, environ: dict[str, Any], raw_id: str) -> Response:
        book = self.repository.get(_parse_id(raw_id))
        if book is None:
            raise _not_found(raw_id)
        return 200, book, []

    def _update_book(self, environ: dict[str, Any], raw_id: str) -> Response:
        book_id = _parse_id(raw_id)
        # Report a missing book before complaining about its replacement body.
        if self.repository.get(book_id) is None:
            raise _not_found(raw_id)
        book = self.repository.update(book_id, _validated_book(environ))
        if book is None:  # deleted by a concurrent request
            raise _not_found(raw_id)
        return 200, book, []

    def _delete_book(self, environ: dict[str, Any], raw_id: str) -> Response:
        if not self.repository.delete(_parse_id(raw_id)):
            raise _not_found(raw_id)
        return 204, None, []


def _not_found(raw_id: str) -> HTTPError:
    return HTTPError(404, f"Book {raw_id} not found")


def _parse_id(raw_id: str) -> int:
    if not _BOOK_ID.match(raw_id):
        raise _not_found(raw_id)
    return int(raw_id)


def _read_json(environ: dict[str, Any]) -> Any:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise HTTPError(400, "Invalid Content-Length header") from None
    if length < 0:
        raise HTTPError(400, "Invalid Content-Length header")
    if length > MAX_BODY_BYTES:
        raise HTTPError(413, f"Request body exceeds {MAX_BODY_BYTES} bytes")
    raw = environ["wsgi.input"].read(length) if length else b""
    if not raw.strip():
        raise HTTPError(400, "Request body must be a JSON object")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise HTTPError(400, "Request body is not valid JSON") from None


def _validated_book(environ: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_book(_read_json(environ))
    except ValidationError as exc:
        raise HTTPError(400, "Validation failed", details=exc.errors) from None


def create_app(db_path: str = "books.db") -> BooksApp:
    """Build the WSGI app with a repository stored at ``db_path``."""
    return BooksApp(BookRepository(db_path))
