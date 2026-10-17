"""HTTP layer: routing, JSON responses and error mapping on top of http.server."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

from .repository import BookRepository
from .validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024
MAX_BOOK_ID = 2**63 - 1  # SQLite INTEGER range; larger ids can never exist.


class ApiError(Exception):
    """An error that maps directly to an HTTP error response."""

    def __init__(self, status: HTTPStatus, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers or {}


@dataclass
class Response:
    status: HTTPStatus
    body: Any = None  # JSON-serialisable. None means the response has no body.
    headers: dict[str, str] = field(default_factory=dict)


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    @property
    def repository(self) -> BookRepository:
        return cast(BookHTTPServer, self.server).repository

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def _dispatch(self, method: str) -> None:
        try:
            response = self._route(method)
        except ApiError as err:
            response = _error(err.status, err.message, headers=err.headers)
        except ValidationError as err:
            response = _error(HTTPStatus.BAD_REQUEST, "Validation failed", details=err.details)
        except Exception:
            logger.exception("Unhandled error for %s %s", method, self.path)
            response = _error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
        self._send(response)

    def _route(self, method: str) -> Response:
        url = urlsplit(self.path)
        parts = [part for part in url.path.split("/") if part]

        handlers: dict[str, Callable[[], Response]]
        if parts == ["health"]:
            handlers = {"GET": self._health}
        elif parts == ["books"]:
            handlers = {
                "GET": partial(self._list_books, url.query),
                "POST": self._create_book,
            }
        elif len(parts) == 2 and parts[0] == "books":
            book_id = _parse_book_id(parts[1])
            if book_id is None:
                raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
            handlers = {
                "GET": partial(self._get_book, book_id),
                "PUT": partial(self._update_book, book_id),
                "DELETE": partial(self._delete_book, book_id),
            }
        else:
            raise ApiError(HTTPStatus.NOT_FOUND, "Route not found")

        handler = handlers.get(method)
        if handler is None:
            allowed = ", ".join(sorted(handlers))
            raise ApiError(
                HTTPStatus.METHOD_NOT_ALLOWED,
                f"Method {method} not allowed",
                headers={"Allow": allowed},
            )
        return handler()

    def _health(self) -> Response:
        if self.repository.ping():
            return Response(HTTPStatus.OK, {"status": "ok"})
        return Response(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable"})

    def _list_books(self, query_string: str) -> Response:
        # parse_qs drops blank values, so ?author= behaves the same as no filter.
        author = (parse_qs(query_string).get("author") or [""])[0].strip() or None
        books = self.repository.list_books(author)
        return Response(HTTPStatus.OK, [book.to_dict() for book in books])

    def _create_book(self) -> Response:
        fields = validate_book(self._read_json())
        book = self.repository.create(fields)
        return Response(HTTPStatus.CREATED, book.to_dict(), {"Location": f"/books/{book.id}"})

    def _get_book(self, book_id: int) -> Response:
        book = self.repository.get(book_id)
        if book is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
        return Response(HTTPStatus.OK, book.to_dict())

    def _update_book(self, book_id: int) -> Response:
        # PUT replaces the whole book, so title and author are required again.
        fields = validate_book(self._read_json())
        book = self.repository.update(book_id, fields)
        if book is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
        return Response(HTTPStatus.OK, book.to_dict())

    def _delete_book(self, book_id: int) -> Response:
        if not self.repository.delete(book_id):
            raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
        return Response(HTTPStatus.NO_CONTENT)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header") from None
        if length < 0:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"Request body exceeds {MAX_BODY_BYTES} bytes")

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
        except ValueError:  # Covers both JSON syntax and UTF-8 decoding errors.
            raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON") from None
        if not isinstance(payload, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")
        return payload

    def _send(self, response: Response) -> None:
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        if response.body is None:
            self.end_headers()
            return

        data = json.dumps(response.body).encode("utf-8")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class BookHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server that gives its request handlers access to the repository."""

    def __init__(self, address: tuple[str, int], repository: BookRepository):
        self.repository = repository
        super().__init__(address, BookRequestHandler)


def create_server(repository: BookRepository, host: str = "127.0.0.1", port: int = 8000) -> BookHTTPServer:
    """Bind a server for ``repository``. Call ``serve_forever()`` to start handling requests."""
    return BookHTTPServer((host, port), repository)


def _parse_book_id(segment: str) -> int | None:
    if not (segment.isascii() and segment.isdigit()):
        return None
    value = int(segment)
    return value if value <= MAX_BOOK_ID else None


def _error(
    status: HTTPStatus,
    message: str,
    details: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    body: dict[str, Any] = {"error": message}
    if details:
        body["details"] = details
    return Response(status, body, headers or {})
