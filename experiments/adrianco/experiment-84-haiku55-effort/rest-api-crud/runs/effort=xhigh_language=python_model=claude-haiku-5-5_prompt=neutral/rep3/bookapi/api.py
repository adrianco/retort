"""Routing and request handling, independent of the HTTP transport.

``BookApi.handle`` turns a method, target and raw body into a ``Response``, so the
whole API can be exercised without opening a socket.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .repository import BookRepository
from .validation import ValidationError, validate_book

log = logging.getLogger(__name__)

# SQLite stores integers as signed 64-bit values; larger IDs cannot exist.
MAX_BOOK_ID = 2**63 - 1

Handler = Callable[[dict[str, str], dict[str, list[str]], bytes], "Response"]


@dataclass(frozen=True)
class Response:
    status: int
    body: Any = None  # JSON-serialisable; None means no body
    headers: dict[str, str] = field(default_factory=dict)


class ApiError(Exception):
    """An expected failure that maps directly to an HTTP status and message."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class BookApi:
    def __init__(self, repository: BookRepository):
        self.repository = repository
        self._routes: list[tuple[re.Pattern[str], dict[str, Handler]]] = [
            (re.compile(r"/books"), {"GET": self._list_books, "POST": self._create_book}),
            (
                re.compile(r"/books/(?P<id>[0-9]+)"),
                {"GET": self._get_book, "PUT": self._update_book, "DELETE": self._delete_book},
            ),
            (re.compile(r"/health"), {"GET": self._health}),
        ]

    def handle(self, method: str, target: str, body: bytes = b"") -> Response:
        """Process one request. ``target`` is the raw request target, path plus query."""
        parts = urlsplit(target)
        path = parts.path.rstrip("/") or "/"
        try:
            handlers, params = self._resolve(path)
            handler = handlers.get(method)
            if handler is None:
                allowed = ", ".join(sorted(handlers))
                return Response(405, {"error": "Method not allowed"}, {"Allow": allowed})
            query = parse_qs(parts.query, keep_blank_values=True)
            return handler(params, query, body)
        except ApiError as exc:
            return Response(exc.status, {"error": exc.message})
        except ValidationError as exc:
            return Response(400, {"error": "Validation failed", "details": exc.errors})
        except Exception:
            log.exception("Unhandled error for %s %s", method, target)
            return Response(500, {"error": "Internal server error"})

    def _resolve(self, path: str) -> tuple[dict[str, Handler], dict[str, str]]:
        for pattern, handlers in self._routes:
            match = pattern.fullmatch(path)
            if match:
                return handlers, match.groupdict()
        raise ApiError(404, "Not found")

    def _list_books(self, params: dict[str, str], query: dict[str, list[str]], body: bytes) -> Response:
        author = query.get("author", [None])[0]
        if author is not None:
            author = author.strip()
            if not author:
                raise ApiError(400, "The author filter must not be empty")
        books = self.repository.list(author)
        return Response(200, [book.to_dict() for book in books])

    def _create_book(self, params: dict[str, str], query: dict[str, list[str]], body: bytes) -> Response:
        fields = validate_book(_decode_json(body))
        book = self.repository.create(fields)
        return Response(201, book.to_dict(), {"Location": f"/books/{book.id}"})

    def _get_book(self, params: dict[str, str], query: dict[str, list[str]], body: bytes) -> Response:
        book = self.repository.get(_book_id(params))
        if book is None:
            raise ApiError(404, "Book not found")
        return Response(200, book.to_dict())

    def _update_book(self, params: dict[str, str], query: dict[str, list[str]], body: bytes) -> Response:
        # PUT replaces the whole book, so title and author are required and
        # omitted year/isbn are cleared.
        book_id = _book_id(params)
        fields = validate_book(_decode_json(body))
        book = self.repository.update(book_id, fields)
        if book is None:
            raise ApiError(404, "Book not found")
        return Response(200, book.to_dict())

    def _delete_book(self, params: dict[str, str], query: dict[str, list[str]], body: bytes) -> Response:
        if not self.repository.delete(_book_id(params)):
            raise ApiError(404, "Book not found")
        return Response(204)

    def _health(self, params: dict[str, str], query: dict[str, list[str]], body: bytes) -> Response:
        try:
            self.repository.ping()
        except Exception:
            log.exception("Health check failed")
            return Response(503, {"status": "unavailable"})
        return Response(200, {"status": "ok"})


def _book_id(params: dict[str, str]) -> int:
    book_id = int(params["id"])
    if book_id > MAX_BOOK_ID:
        # Cannot exist, so report it as missing rather than failing in SQLite.
        raise ApiError(404, "Book not found")
    return book_id


def _decode_json(body: bytes) -> Any:
    try:
        return json.loads(body)
    except (ValueError, RecursionError):  # bad JSON, invalid UTF-8 or absurd nesting
        raise ApiError(400, "Request body must be valid JSON") from None
