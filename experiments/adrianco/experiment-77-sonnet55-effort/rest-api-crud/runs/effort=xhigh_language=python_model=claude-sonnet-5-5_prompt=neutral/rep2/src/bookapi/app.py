"""WSGI application exposing the book collection as a JSON REST API."""

from __future__ import annotations

import json
import logging
import re
from http import HTTPStatus
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs

from .db import BookStore
from .validation import validate_book

log = logging.getLogger("bookapi")

MAX_BODY_BYTES = 1024 * 1024

_BOOK_PATH = re.compile(r"/books/([0-9]+)")

Response = tuple[int, dict[str, str], Any]


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        message: str,
        details: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or {}


class BookApp:
    """WSGI callable. Routes requests to handlers and renders JSON responses."""

    def __init__(self, store: BookStore) -> None:
        self.store = store

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
        try:
            status, headers, payload = self._dispatch(environ)
        except ApiError as exc:
            body: dict[str, Any] = {"error": exc.message}
            if exc.details:
                body["details"] = exc.details
            status, headers, payload = exc.status, exc.headers, body
        except Exception:
            log.exception("unhandled error for %s %s", environ.get("REQUEST_METHOD"), environ.get("PATH_INFO"))
            status, headers, payload = 500, {}, {"error": "internal server error"}

        headers = dict(headers)
        if status == HTTPStatus.NO_CONTENT:
            data = b""
        else:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(data))

        phrase = HTTPStatus(status).phrase
        start_response(f"{status} {phrase}", list(headers.items()))
        return [data]

    # -- routing -----------------------------------------------------------

    def _dispatch(self, environ: dict[str, Any]) -> Response:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            routes = {"GET": self._health}
        elif path == "/books":
            routes = {"GET": self._list_books, "POST": self._create_book}
        elif match := _BOOK_PATH.fullmatch(path):
            book_id = int(match.group(1))
            routes = {
                "GET": lambda env: self._get_book(book_id),
                "PUT": lambda env: self._update_book(book_id, env),
                "DELETE": lambda env: self._delete_book(book_id),
            }
        else:
            raise ApiError(404, "not found")

        handler = routes.get(method)
        if handler is None:
            raise ApiError(405, "method not allowed", headers={"Allow": ", ".join(routes)})
        return handler(environ)

    # -- handlers ----------------------------------------------------------

    def _health(self, environ: dict[str, Any]) -> Response:
        try:
            self.store.ping()
        except Exception:
            log.exception("health check failed")
            return 503, {}, {"status": "unavailable"}
        return 200, {}, {"status": "ok"}

    def _list_books(self, environ: dict[str, Any]) -> Response:
        query = parse_qs(environ.get("QUERY_STRING", ""))
        author = query.get("author", [None])[0]
        return 200, {}, self.store.list_books(author)

    def _create_book(self, environ: dict[str, Any]) -> Response:
        clean, errors = validate_book(self._read_json(environ))
        if errors:
            raise ApiError(400, "validation failed", errors)
        book = self.store.create(**clean)
        return 201, {"Location": f"/books/{book['id']}"}, book

    def _get_book(self, book_id: int) -> Response:
        return 200, {}, self._require(self.store.get(book_id))

    def _update_book(self, book_id: int, environ: dict[str, Any]) -> Response:
        clean, errors = validate_book(self._read_json(environ), partial=True)
        if errors:
            raise ApiError(400, "validation failed", errors)
        return 200, {}, self._require(self.store.update(book_id, clean))

    def _delete_book(self, book_id: int) -> Response:
        if not self.store.delete(book_id):
            raise ApiError(404, "book not found")
        return 204, {}, None

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _require(book: dict[str, Any] | None) -> dict[str, Any]:
        if book is None:
            raise ApiError(404, "book not found")
        return book

    @staticmethod
    def _read_json(environ: dict[str, Any]) -> Any:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise ApiError(400, "invalid Content-Length header") from None
        if length < 0:
            raise ApiError(400, "invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise ApiError(413, f"request body exceeds {MAX_BODY_BYTES} bytes")
        raw = environ["wsgi.input"].read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, RecursionError):
            raise ApiError(400, "request body must be valid JSON") from None
