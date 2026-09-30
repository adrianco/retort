"""WSGI application exposing the book collection REST API."""

import json
import logging
import re
import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from .db import BookRepository
from .validation import validate_book

MAX_BODY_BYTES = 1_000_000
_MAX_SQLITE_INT = 2**63 - 1

log = logging.getLogger(__name__)


class ApiError(Exception):
    """An error that maps directly onto an HTTP error response."""

    def __init__(
        self,
        status: HTTPStatus,
        message: str,
        details: dict[str, str] | None = None,
        headers: Iterable[tuple[str, str]] = (),
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = list(headers)


@dataclass
class Response:
    status: HTTPStatus
    body: Any = None
    headers: list[tuple[str, str]] = field(default_factory=list)


class Request:
    def __init__(self, environ: dict[str, Any]) -> None:
        self.environ = environ

    @property
    def query(self) -> dict[str, str]:
        parsed = parse_qs(self.environ.get("QUERY_STRING", ""), keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    def json(self) -> dict[str, Any]:
        """Read the body as a JSON object, raising ApiError(400/413) otherwise."""
        try:
            length = int(self.environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
        if length < 0:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                f"Request body must be at most {MAX_BODY_BYTES} bytes",
            )
        raw = self.environ["wsgi.input"].read(length) if length else b""
        if not raw.strip():
            raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Request body is not valid JSON")
        if not isinstance(data, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")
        return data


def _parse_book_id(raw: str) -> int:
    """Path ids that are not positive integers can never match a book -> 404."""
    if not (raw.isascii() and raw.isdigit()) or len(raw) > 19:
        raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
    book_id = int(raw)
    if book_id > _MAX_SQLITE_INT:
        raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
    return book_id


def _not_found() -> ApiError:
    return ApiError(HTTPStatus.NOT_FOUND, "Book not found")


Handler = Callable[..., Response]


class BookApp:
    """WSGI callable serving the books API on top of a BookRepository."""

    def __init__(self, repository: BookRepository) -> None:
        self.repository = repository
        self._routes: list[tuple[re.Pattern[str], dict[str, Handler]]] = [
            (re.compile(r"/health"), {"GET": self._health}),
            (
                re.compile(r"/books"),
                {"GET": self._list_books, "POST": self._create_book},
            ),
            (
                re.compile(r"/books/(?P<book_id>[^/]+)"),
                {
                    "GET": self._get_book,
                    "PUT": self._update_book,
                    "DELETE": self._delete_book,
                },
            ),
        ]

    # -- WSGI entry point ---------------------------------------------------

    def __call__(self, environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        try:
            response = self._dispatch(method, environ)
        except ApiError as exc:
            body: dict[str, Any] = {"error": exc.message}
            if exc.details:
                body["details"] = exc.details
            response = Response(exc.status, body, exc.headers)
        except Exception:
            log.exception("Unhandled error serving %s %s", method, environ.get("PATH_INFO"))
            response = Response(
                HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"}
            )
        return self._send(start_response, response, head_only=method == "HEAD")

    def close(self) -> None:
        self.repository.close()

    # -- routing --------------------------------------------------------------

    def _dispatch(self, method: str, environ: dict[str, Any]) -> Response:
        path = environ.get("PATH_INFO", "") or "/"
        if len(path) > 1:
            path = path.rstrip("/")
        for pattern, handlers in self._routes:
            match = pattern.fullmatch(path)
            if not match:
                continue
            # HEAD is served as GET with the body dropped in __call__.
            handler = handlers.get("GET" if method == "HEAD" else method)
            if handler is None:
                allowed = sorted({*handlers, *(["HEAD"] if "GET" in handlers else [])})
                raise ApiError(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    f"Method {method} not allowed",
                    headers=[("Allow", ", ".join(allowed))],
                )
            return handler(Request(environ), **match.groupdict())
        raise ApiError(HTTPStatus.NOT_FOUND, "Not found")

    @staticmethod
    def _send(start_response: Callable, response: Response, head_only: bool) -> list[bytes]:
        status = response.status
        headers = list(response.headers)
        payload = b""
        if response.body is not None:
            payload = json.dumps(response.body).encode("utf-8")
            headers.append(("Content-Type", "application/json"))
        if status != HTTPStatus.NO_CONTENT:
            headers.append(("Content-Length", str(len(payload))))
        start_response(f"{status.value} {status.phrase}", headers)
        return [] if head_only or not payload else [payload]

    # -- handlers -------------------------------------------------------------

    def _health(self, request: Request) -> Response:
        try:
            self.repository.ping()
        except sqlite3.Error:
            log.exception("Health check failed")
            return Response(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable"})
        return Response(HTTPStatus.OK, {"status": "ok"})

    def _list_books(self, request: Request) -> Response:
        author = request.query.get("author", "").strip() or None
        return Response(HTTPStatus.OK, self.repository.list_books(author=author))

    def _create_book(self, request: Request) -> Response:
        fields, errors = validate_book(request.json())
        if errors:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Validation failed", errors)
        book = self.repository.create(**fields)
        return Response(
            HTTPStatus.CREATED, book, [("Location", f"/books/{book['id']}")]
        )

    def _get_book(self, request: Request, book_id: str) -> Response:
        book = self.repository.get(_parse_book_id(book_id))
        if book is None:
            raise _not_found()
        return Response(HTTPStatus.OK, book)

    def _update_book(self, request: Request, book_id: str) -> Response:
        """PUT applies the fields sent; omitted fields keep their current value."""
        book_id_int = _parse_book_id(book_id)
        if self.repository.get(book_id_int) is None:
            raise _not_found()
        payload = request.json()
        fields, errors = validate_book(payload, partial=True)
        if not errors and not fields:
            errors = {"body": "Provide at least one of: title, author, year, isbn"}
        if errors:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Validation failed", errors)
        book = self.repository.update(book_id_int, fields)
        if book is None:  # deleted between the existence check and the update
            raise _not_found()
        return Response(HTTPStatus.OK, book)

    def _delete_book(self, request: Request, book_id: str) -> Response:
        if not self.repository.delete(_parse_book_id(book_id)):
            raise _not_found()
        return Response(HTTPStatus.NO_CONTENT)


def create_app(db_path: str = ":memory:") -> BookApp:
    """Build the WSGI app, opening (and creating, if needed) the SQLite DB."""
    return BookApp(BookRepository(db_path))
