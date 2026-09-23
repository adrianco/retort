"""Routing and request handling, independent of the HTTP server.

``BooksApp.handle(method, target, body)`` takes a raw request and returns a
``Response``. That keeps the API logic testable without opening sockets, while
``books_api.server`` connects it to ``http.server``.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from .db import BookRepository
from .validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

JSON_CONTENT_TYPE = "application/json"
MAX_SQLITE_INTEGER = 2**63 - 1
_BOOK_PATH = re.compile(r"/books/([^/]+)")
_ID = re.compile(r"[0-9]+")


@dataclass
class Response:
    status: int
    payload: Any = None
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def body(self) -> bytes:
        if self.payload is None:
            return b""
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    body: bytes

    def query_param(self, name: str) -> str | None:
        values = self.query.get(name)
        return values[0] if values else None


class HTTPError(Exception):
    """An error that maps directly to an HTTP status code and a JSON error body."""

    def __init__(
        self,
        status: int,
        message: str,
        *,
        details: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or {}

    def to_response(self) -> Response:
        payload: dict[str, Any] = {"error": self.message}
        if self.details:
            payload["details"] = self.details
        return Response(self.status, payload, dict(self.headers))


Handler = Callable[..., Response]


class BooksApp:
    def __init__(self, repository: BookRepository):
        self.repository = repository

    def handle(self, method: str, target: str, body: bytes = b"") -> Response:
        """Handle one request. ``target`` is the request path including any query string."""
        url = urlsplit(target)
        request = Request(
            method=method.upper(),
            path=url.path.rstrip("/") or "/",
            query=parse_qs(url.query),
            body=body,
        )
        try:
            return self._route(request)
        except HTTPError as exc:
            return exc.to_response()
        except Exception:
            logger.exception("Unhandled error processing %s %s", method, target)
            return Response(500, {"error": "Internal server error"})

    # -- routing -----------------------------------------------------------

    def _route(self, request: Request) -> Response:
        if request.path == "/health":
            return self._dispatch(request, {"GET": self._health})
        if request.path == "/books":
            return self._dispatch(request, {"GET": self._list_books, "POST": self._create_book})
        match = _BOOK_PATH.fullmatch(request.path)
        if match:
            book_id = _parse_book_id(match.group(1))
            handlers = {"GET": self._get_book, "PUT": self._update_book, "DELETE": self._delete_book}
            return self._dispatch(request, handlers, book_id)
        raise HTTPError(404, "Not found")

    @staticmethod
    def _dispatch(request: Request, handlers: dict[str, Handler], *args: Any) -> Response:
        allowed = set(handlers) | {"OPTIONS"}
        if "GET" in allowed:
            allowed.add("HEAD")
        allow = ", ".join(sorted(allowed))
        if request.method == "OPTIONS":
            return Response(204, headers={"Allow": allow})
        # HEAD runs the GET handler; the HTTP layer sends the headers without the body.
        handler = handlers.get("GET" if request.method == "HEAD" else request.method)
        if handler is None:
            raise HTTPError(405, f"Method {request.method} not allowed", headers={"Allow": allow})
        return handler(request, *args)

    # -- handlers ----------------------------------------------------------

    def _health(self, request: Request) -> Response:
        try:
            self.repository.ping()
        except sqlite3.Error:
            logger.exception("Health check failed")
            return Response(503, {"status": "unavailable", "database": "error"})
        return Response(200, {"status": "ok", "database": "ok"})

    def _list_books(self, request: Request) -> Response:
        author = (request.query_param("author") or "").strip()
        return Response(200, self.repository.list_books(author=author or None))

    def _create_book(self, request: Request) -> Response:
        data = _validated(_parse_json(request.body), partial=False)
        book = self.repository.create_book(data)
        return Response(201, book, {"Location": f"/books/{book['id']}"})

    def _get_book(self, request: Request, book_id: int) -> Response:
        book = self.repository.get_book(book_id)
        if book is None:
            raise _book_not_found()
        return Response(200, book)

    def _update_book(self, request: Request, book_id: int) -> Response:
        changes = _validated(_parse_json(request.body), partial=True)
        book = self.repository.update_book(book_id, changes)
        if book is None:
            raise _book_not_found()
        return Response(200, book)

    def _delete_book(self, request: Request, book_id: int) -> Response:
        if not self.repository.delete_book(book_id):
            raise _book_not_found()
        return Response(204)


def _book_not_found() -> HTTPError:
    return HTTPError(404, "Book not found")


def _parse_book_id(raw: str) -> int:
    # Anything that cannot be a stored id (non-numeric, or too large for SQLite's
    # 64-bit INTEGER) names a resource that doesn't exist.
    if not _ID.fullmatch(raw) or int(raw) > MAX_SQLITE_INTEGER:
        raise _book_not_found()
    return int(raw)


def _reject_constant(name: str) -> None:
    raise ValueError(f"{name} is not valid JSON")


def _parse_json(body: bytes) -> Any:
    if not body.strip():
        raise HTTPError(400, "Request body must be a JSON object")
    try:
        # json.loads accepts NaN/Infinity by default although JSON doesn't allow them.
        return json.loads(body, parse_constant=_reject_constant)
    except ValueError:  # includes JSONDecodeError and UnicodeDecodeError
        raise HTTPError(400, "Request body is not valid JSON") from None


def _validated(payload: Any, *, partial: bool) -> dict[str, Any]:
    try:
        return validate_book(payload, partial=partial)
    except ValidationError as exc:
        raise HTTPError(400, "Validation failed", details=exc.errors) from None
