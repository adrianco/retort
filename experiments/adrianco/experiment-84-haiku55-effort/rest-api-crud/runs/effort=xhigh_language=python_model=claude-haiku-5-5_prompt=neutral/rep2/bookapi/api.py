"""Request handling for the books API.

This layer knows about routes, status codes and JSON bodies, but nothing about
sockets, so it can be exercised directly in tests.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .db import BookRepository
from .validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024
# SQLite ids are signed 64-bit integers, so larger ids cannot exist.
MAX_BOOK_ID = 2**63 - 1

_BOOK_PATH = re.compile(r"/books/([0-9]+)")
_BOOK_NOT_FOUND = "Book not found"


@dataclass
class Response:
    """An HTTP-independent response. A body of None means no content."""

    status: int
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)


class ApiError(Exception):
    """Raised inside a handler to produce an error response."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class BooksApi:
    """Maps (method, target, body) onto repository operations."""

    def __init__(self, repo: BookRepository) -> None:
        self.repo = repo

    def close(self) -> None:
        self.repo.close()

    def handle(self, method: str, target: str, body: bytes = b"") -> Response:
        url = urlsplit(target)
        path = url.path.rstrip("/") or "/"
        try:
            return self._route(method.upper(), path, url.query, body)
        except ValidationError as exc:
            return Response(400, {"error": "Validation failed", "details": exc.errors})
        except ApiError as exc:
            return Response(exc.status, {"error": exc.message})
        except Exception:
            logger.exception("Unhandled error for %s %s", method, target)
            return Response(500, {"error": "Internal server error"})

    def _route(self, method: str, path: str, query: str, body: bytes) -> Response:
        if path == "/health":
            return _dispatch(method, {"GET": self._health})
        if path == "/books":
            return _dispatch(method, {
                "GET": lambda: self._search_books(query),
                "POST": lambda: self._create_book(body),
            })
        match = _BOOK_PATH.fullmatch(path)
        if match is not None:
            book_id = int(match.group(1))
            if book_id > MAX_BOOK_ID:
                raise ApiError(404, _BOOK_NOT_FOUND)
            return _dispatch(method, {
                "GET": lambda: self._get_book(book_id),
                "PUT": lambda: self._update_book(book_id, body),
                "DELETE": lambda: self._delete_book(book_id),
            })
        raise ApiError(404, "Not found")

    def _health(self) -> Response:
        if self.repo.ping():
            return Response(200, {"status": "ok"})
        return Response(503, {"status": "unavailable"})

    def _search_books(self, query: str) -> Response:
        author = parse_qs(query).get("author", [""])[0].strip()
        return Response(200, self.repo.search(author or None))

    def _create_book(self, body: bytes) -> Response:
        book = self.repo.create(validate_book(_parse_json(body)))
        return Response(201, book, {"Location": f"/books/{book['id']}"})

    def _get_book(self, book_id: int) -> Response:
        book = self.repo.get(book_id)
        if book is None:
            raise ApiError(404, _BOOK_NOT_FOUND)
        return Response(200, book)

    def _update_book(self, book_id: int, body: bytes) -> Response:
        book = self.repo.update(book_id, validate_book(_parse_json(body)))
        if book is None:
            raise ApiError(404, _BOOK_NOT_FOUND)
        return Response(200, book)

    def _delete_book(self, book_id: int) -> Response:
        if not self.repo.delete(book_id):
            raise ApiError(404, _BOOK_NOT_FOUND)
        return Response(204)


def _dispatch(method: str, handlers: dict[str, Callable[[], Response]]) -> Response:
    handler = handlers.get(method)
    if handler is None:
        allowed = ", ".join(sorted(handlers))
        return Response(405, {"error": "Method not allowed"}, {"Allow": allowed})
    return handler()


def _parse_json(body: bytes) -> Any:
    try:
        return json.loads(body)
    except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError both subclass ValueError
        raise ApiError(400, "Request body must be valid JSON") from exc
