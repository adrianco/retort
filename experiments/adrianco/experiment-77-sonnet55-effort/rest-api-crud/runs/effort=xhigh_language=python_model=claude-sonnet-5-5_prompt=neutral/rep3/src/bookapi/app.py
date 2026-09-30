"""WSGI application exposing the book collection as a JSON REST API."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs

from .store import BookStore
from .validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1_048_576

_STATUS_TEXT = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    413: "Payload Too Large",
    500: "Internal Server Error",
    503: "Service Unavailable",
}

_BOOK_PATH = re.compile(r"^/books/(?P<id>[^/]+)$")

Response = tuple[int, Any, list[tuple[str, str]]]


class HTTPError(Exception):
    def __init__(self, status: int, message: str, extra: dict[str, Any] | None = None,
                 headers: list[tuple[str, str]] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = {"error": message, **(extra or {})}
        self.headers = headers or []


class BookApp:
    """WSGI callable; all state lives in the injected :class:`BookStore`."""

    def __init__(self, store: BookStore) -> None:
        self.store = store

    # -- WSGI entry point ---------------------------------------------------

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
        try:
            status, payload, headers = self._dispatch(environ)
        except HTTPError as exc:
            status, payload, headers = exc.status, exc.body, exc.headers
        except Exception:
            logger.exception("Unhandled error while serving %s %s",
                             environ.get("REQUEST_METHOD"), environ.get("PATH_INFO"))
            status, payload, headers = 500, {"error": "Internal server error"}, []

        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = list(headers)
        if body:
            headers.append(("Content-Type", "application/json; charset=utf-8"))
        headers.append(("Content-Length", str(len(body))))
        start_response(f"{status} {_STATUS_TEXT[status]}", headers)
        return [body]

    # -- routing ------------------------------------------------------------

    def _dispatch(self, environ: dict[str, Any]) -> Response:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            self._require_method(method, ("GET",))
            return self._health()

        if path == "/books":
            self._require_method(method, ("GET", "POST"))
            if method == "POST":
                return self._create_book(environ)
            return self._list_books(environ)

        match = _BOOK_PATH.match(path)
        if match:
            self._require_method(method, ("GET", "PUT", "DELETE"))
            book_id = self._parse_id(match["id"])
            if method == "GET":
                return self._get_book(book_id)
            if method == "PUT":
                return self._update_book(book_id, environ)
            return self._delete_book(book_id)

        raise HTTPError(404, "Not found")

    @staticmethod
    def _require_method(method: str, allowed: tuple[str, ...]) -> None:
        if method not in allowed:
            raise HTTPError(405, f"Method {method} not allowed",
                            headers=[("Allow", ", ".join(allowed))])

    @staticmethod
    def _parse_id(raw: str) -> int:
        # An id that is not a plain non-negative integer can never name a book.
        if not (raw.isascii() and raw.isdigit()):
            raise HTTPError(404, "Book not found")
        return int(raw)

    # -- handlers -----------------------------------------------------------

    def _health(self) -> Response:
        try:
            self.store.ping()
        except sqlite3.Error:
            logger.exception("Health check failed")
            return 503, {"status": "unavailable"}, []
        return 200, {"status": "ok"}, []

    def _create_book(self, environ: dict[str, Any]) -> Response:
        book = self._validated_body(environ)
        created = self.store.create(book)
        return 201, created, [("Location", f"/books/{created['id']}")]

    def _list_books(self, environ: dict[str, Any]) -> Response:
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        author = query.get("author", [""])[0].strip()
        return 200, self.store.list_books(author or None), []

    def _get_book(self, book_id: int) -> Response:
        return 200, self._existing(book_id), []

    def _update_book(self, book_id: int, environ: dict[str, Any]) -> Response:
        self._existing(book_id)
        book = self._validated_body(environ)
        updated = self.store.update(book_id, book)
        if updated is None:  # deleted between the check and the update
            raise HTTPError(404, "Book not found")
        return 200, updated, []

    def _delete_book(self, book_id: int) -> Response:
        if not self.store.delete(book_id):
            raise HTTPError(404, "Book not found")
        return 204, None, []

    # -- helpers ------------------------------------------------------------

    def _existing(self, book_id: int) -> dict[str, Any]:
        book = self.store.get(book_id)
        if book is None:
            raise HTTPError(404, "Book not found")
        return book

    def _validated_body(self, environ: dict[str, Any]) -> dict[str, Any]:
        try:
            return validate_book(self._read_json(environ))
        except ValidationError as exc:
            raise HTTPError(400, "Validation failed", {"details": exc.errors}) from None

    @staticmethod
    def _read_json(environ: dict[str, Any]) -> Any:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HTTPError(400, "Invalid Content-Length header") from None
        if length < 0:
            raise HTTPError(400, "Invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise HTTPError(413, f"Request body must be at most {MAX_BODY_BYTES} bytes")
        raw = environ["wsgi.input"].read(length) if length else b""
        if not raw.strip():
            raise HTTPError(400, "Request body must be a JSON object")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise HTTPError(400, "Request body is not valid JSON") from None
