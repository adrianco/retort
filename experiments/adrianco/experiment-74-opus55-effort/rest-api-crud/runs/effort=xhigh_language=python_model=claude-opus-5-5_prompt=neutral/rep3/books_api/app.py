"""WSGI application implementing the book collection REST API.

Routes:
    GET    /health
    GET    /books            (optional ?author= filter)
    POST   /books
    GET    /books/{id}
    PUT    /books/{id}
    DELETE /books/{id}
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from .storage import BookRepository
from .validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024
# Largest id SQLite can store; anything bigger can't exist (and would overflow).
MAX_BOOK_ID = 2**63 - 1

Environ = dict[str, Any]
StartResponse = Callable[..., Any]
Headers = list[tuple[str, str]]


@dataclass
class Response:
    status: int
    payload: Any = None
    headers: Headers = field(default_factory=list)


class HTTPError(Exception):
    """An error that maps directly onto an HTTP error response."""

    def __init__(
        self,
        status: int,
        message: str,
        *,
        details: dict[str, str] | None = None,
        headers: Headers | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []

    def to_response(self) -> Response:
        payload: dict[str, Any] = {"error": self.message}
        if self.details:
            payload["details"] = self.details
        return Response(self.status, payload, self.headers)


class BookAPI:
    """The WSGI application. Serve it with any WSGI server."""

    def __init__(self, repository: BookRepository) -> None:
        self.repository = repository
        self._routes: list[tuple[re.Pattern[str], dict[str, Callable[..., Response]]]] = [
            (re.compile(r"/health/?"), {"GET": self.health}),
            (
                re.compile(r"/books/?"),
                {"GET": self.list_books, "POST": self.create_book},
            ),
            (
                re.compile(r"/books/(?P<book_id>[0-9]+)/?"),
                {"GET": self.get_book, "PUT": self.update_book, "DELETE": self.delete_book},
            ),
        ]

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterable[bytes]:
        try:
            response = self._dispatch(environ)
        except ValidationError as exc:
            response = HTTPError(400, exc.message, details=exc.errors).to_response()
        except HTTPError as exc:
            response = exc.to_response()
        except Exception:
            logger.exception(
                "Unhandled error for %s %s",
                environ.get("REQUEST_METHOD"),
                environ.get("PATH_INFO"),
            )
            response = HTTPError(500, "Internal server error").to_response()
        return _send(response, start_response)

    def _dispatch(self, environ: Environ) -> Response:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO") or "/"
        for pattern, handlers in self._routes:
            match = pattern.fullmatch(path)
            if match is None:
                continue
            handler = handlers.get(method)
            if handler is None:
                raise HTTPError(
                    405,
                    f"Method {method} is not allowed on {path}",
                    headers=[("Allow", ", ".join(handlers))],
                )
            return handler(environ, **match.groupdict())
        raise HTTPError(404, f"Resource {path} not found")

    # -- handlers ---------------------------------------------------------

    def health(self, environ: Environ) -> Response:
        if self.repository.ping():
            return Response(200, {"status": "ok", "database": "ok"})
        return Response(503, {"status": "unavailable", "database": "unreachable"})

    def list_books(self, environ: Environ) -> Response:
        query = parse_qs(environ.get("QUERY_STRING", ""))
        author = query.get("author", [""])[0].strip() or None
        return Response(200, self.repository.list_all(author=author))

    def create_book(self, environ: Environ) -> Response:
        fields = validate_book(_read_json(environ))
        book = self.repository.create(fields)
        return Response(201, book, [("Location", f"/books/{book['id']}")])

    def get_book(self, environ: Environ, book_id: str) -> Response:
        book = self.repository.get(_parse_book_id(book_id))
        if book is None:
            raise _book_not_found(book_id)
        return Response(200, book)

    def update_book(self, environ: Environ, book_id: str) -> Response:
        parsed_id = _parse_book_id(book_id)
        fields = validate_book(_read_json(environ))
        book = self.repository.update(parsed_id, fields)
        if book is None:
            raise _book_not_found(book_id)
        return Response(200, book)

    def delete_book(self, environ: Environ, book_id: str) -> Response:
        if not self.repository.delete(_parse_book_id(book_id)):
            raise _book_not_found(book_id)
        return Response(204)


def _parse_book_id(raw: str) -> int:
    book_id = int(raw)
    if book_id > MAX_BOOK_ID:
        raise _book_not_found(raw)
    return book_id


def _book_not_found(book_id: str) -> HTTPError:
    return HTTPError(404, f"Book {book_id} not found")


def _read_json(environ: Environ) -> Any:
    """Decode the request body as JSON, enforcing content type and size."""
    media_type = environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise HTTPError(415, "Content-Type must be application/json")

    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise HTTPError(400, "Invalid Content-Length header") from None
    if length < 0:
        raise HTTPError(400, "Invalid Content-Length header")
    if length > MAX_BODY_BYTES:
        raise HTTPError(413, f"Request body must not exceed {MAX_BODY_BYTES} bytes")

    body = environ["wsgi.input"].read(length) if length else b""
    if not body.strip():
        raise HTTPError(400, "Request body must be a JSON object")
    try:
        return json.loads(body)
    except (ValueError, RecursionError):
        # ValueError covers JSONDecodeError and UnicodeDecodeError.
        raise HTTPError(400, "Request body is not valid JSON") from None


def _send(response: Response, start_response: StartResponse) -> list[bytes]:
    status = f"{response.status} {HTTPStatus(response.status).phrase}"
    headers = list(response.headers)
    if response.status == 204:
        start_response(status, headers)
        return []
    body = json.dumps(response.payload, ensure_ascii=False).encode("utf-8")
    headers += [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status, headers)
    return [body]
