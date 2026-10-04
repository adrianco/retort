"""WSGI application exposing the book collection as a JSON REST API."""

import json
import logging
import re
import sqlite3
from http import HTTPStatus
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs

from bookapi.store import BookStore
from bookapi.validation import validate_book

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024

_BOOK_PATH = re.compile(r"/books/([0-9]+)")

Response = tuple[HTTPStatus, Any, list[tuple[str, str]]]


class APIError(Exception):
    """An error that maps directly onto a JSON error response."""

    def __init__(
        self,
        status: HTTPStatus,
        message: str,
        details: dict[str, str] | None = None,
        headers: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []

    def response(self) -> Response:
        body: dict[str, Any] = {"error": self.message}
        if self.details:
            body["details"] = self.details
        return self.status, body, self.headers


class BookAPI:
    """WSGI callable. Create one per :class:`BookStore`."""

    def __init__(self, store: BookStore) -> None:
        self._store = store

    def __call__(
        self, environ: dict[str, Any], start_response: Callable[..., Any]
    ) -> Iterable[bytes]:
        try:
            status, body, headers = self._dispatch(environ)
        except APIError as exc:
            status, body, headers = exc.response()
        except Exception:
            # Never leak internals to the client; the traceback goes to the log.
            logger.exception("Unhandled error processing request")
            status, body, headers = APIError(
                HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
            ).response()

        payload = b""
        headers = list(headers)
        if status != HTTPStatus.NO_CONTENT:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers.append(("Content-Type", "application/json; charset=utf-8"))
            headers.append(("Content-Length", str(len(payload))))
        start_response(f"{status.value} {status.phrase}", headers)
        if environ.get("REQUEST_METHOD") == "HEAD":
            return []
        return [payload]

    # -- routing ---------------------------------------------------------

    def _dispatch(self, environ: dict[str, Any]) -> Response:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        if method == "HEAD":
            # HEAD is GET without the body; __call__ drops the payload.
            method = "GET"
        path = environ.get("PATH_INFO") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            return self._route(method, {"GET": lambda: self._health()})
        if path == "/books":
            return self._route(
                method,
                {
                    "GET": lambda: self._list_books(environ),
                    "POST": lambda: self._create_book(environ),
                },
            )
        match = _BOOK_PATH.fullmatch(path)
        if match:
            book_id = int(match.group(1))
            return self._route(
                method,
                {
                    "GET": lambda: self._get_book(book_id),
                    "PUT": lambda: self._update_book(book_id, environ),
                    "DELETE": lambda: self._delete_book(book_id),
                },
            )
        raise APIError(HTTPStatus.NOT_FOUND, "Resource not found")

    @staticmethod
    def _route(method: str, handlers: dict[str, Callable[[], Response]]) -> Response:
        handler = handlers.get(method)
        if handler is None:
            raise APIError(
                HTTPStatus.METHOD_NOT_ALLOWED,
                f"Method {method} not allowed",
                headers=[("Allow", ", ".join(handlers))],
            )
        return handler()

    # -- handlers --------------------------------------------------------

    def _health(self) -> Response:
        try:
            self._store.ping()
        except sqlite3.Error:
            logger.exception("Health check failed")
            raise APIError(
                HTTPStatus.SERVICE_UNAVAILABLE, "Database unavailable"
            ) from None
        return HTTPStatus.OK, {"status": "ok"}, []

    def _list_books(self, environ: dict[str, Any]) -> Response:
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        # A blank ?author= is treated as "no filter" rather than "match nothing".
        author = query.get("author", [""])[0].strip() or None
        return HTTPStatus.OK, self._store.list(author=author), []

    def _create_book(self, environ: dict[str, Any]) -> Response:
        book = self._store.create(_read_book(environ))
        return HTTPStatus.CREATED, book, [("Location", f"/books/{book['id']}")]

    def _get_book(self, book_id: int) -> Response:
        book = self._store.get(book_id)
        if book is None:
            raise _not_found(book_id)
        return HTTPStatus.OK, book, []

    def _update_book(self, book_id: int, environ: dict[str, Any]) -> Response:
        book = self._store.update(book_id, _read_book(environ))
        if book is None:
            raise _not_found(book_id)
        return HTTPStatus.OK, book, []

    def _delete_book(self, book_id: int) -> Response:
        if not self._store.delete(book_id):
            raise _not_found(book_id)
        return HTTPStatus.NO_CONTENT, None, []


def _not_found(book_id: int) -> APIError:
    return APIError(HTTPStatus.NOT_FOUND, f"Book {book_id} not found")


def _read_book(environ: dict[str, Any]) -> dict[str, Any]:
    """Read, parse and validate the request body as a book."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise APIError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length") from None
    if length < 0:
        raise APIError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
    if length > MAX_BODY_BYTES:
        raise APIError(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            f"Request body must be at most {MAX_BODY_BYTES} bytes",
        )

    raw = environ["wsgi.input"].read(length) if length else b""
    try:
        payload = json.loads(raw)
    except (ValueError, RecursionError):
        raise APIError(
            HTTPStatus.BAD_REQUEST, "Request body must be valid JSON"
        ) from None

    book, errors = validate_book(payload)
    if errors:
        raise APIError(HTTPStatus.BAD_REQUEST, "Validation failed", details=errors)
    return book
