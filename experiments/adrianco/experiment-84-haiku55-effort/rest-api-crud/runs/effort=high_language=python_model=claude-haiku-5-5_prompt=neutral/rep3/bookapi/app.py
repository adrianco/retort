"""WSGI application exposing the book collection as a JSON REST API."""

import json
import logging
import re
import sqlite3
from http import HTTPStatus
from urllib.parse import parse_qs

from .validation import ValidationError, validate_book

MAX_BODY_BYTES = 1_000_000
MAX_BOOK_ID = 2**63 - 1  # SQLite INTEGER limit; larger ids cannot exist.
JSON_CONTENT_TYPE = "application/json; charset=utf-8"

logger = logging.getLogger(__name__)

# (path pattern, {HTTP method: BookApp handler name}). Patterns are matched with fullmatch.
ROUTES = [
    (re.compile(r"/health"), {"GET": "_health"}),
    (re.compile(r"/books"), {"GET": "_list_books", "POST": "_create_book"}),
    (
        re.compile(r"/books/(?P<book_id>[^/]+)"),
        {"GET": "_get_book", "PUT": "_update_book", "DELETE": "_delete_book"},
    ),
]


class HttpError(Exception):
    def __init__(self, status, message, headers=()):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = list(headers)


class BookApp:
    def __init__(self, store):
        self.store = store

    def __call__(self, environ, start_response):
        try:
            status, headers, body = self._handle(environ)
        except HttpError as err:
            status, headers, body = _json(err.status, {"error": err.message}, err.headers)
        except ValidationError as err:
            payload = {"error": "validation failed", "details": err.errors}
            status, headers, body = _json(400, payload)
        except Exception:
            logger.exception("unhandled error while serving request")
            status, headers, body = _json(500, {"error": "internal server error"})
        start_response(status, headers)
        return [body]

    def _handle(self, environ):
        method = environ["REQUEST_METHOD"].upper()
        handlers, params = _match_route(environ.get("PATH_INFO") or "/")
        handler_name = handlers.get(method)
        if handler_name is None:
            allow = ", ".join(sorted(handlers))
            raise HttpError(405, f"method {method} not allowed", [("Allow", allow)])
        code, payload, headers = getattr(self, handler_name)(environ, **params)
        return _json(code, payload, headers)

    def _health(self, environ):
        try:
            self.store.ping()
        except sqlite3.Error:
            logger.exception("health check failed")
            return 503, {"status": "unavailable"}, ()
        return 200, {"status": "ok"}, ()

    def _list_books(self, environ):
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        author = None
        if "author" in query:
            author = query["author"][-1].strip()
            if not author:
                raise HttpError(400, "author filter must not be empty")
        return 200, self.store.list_books(author=author), ()

    def _get_book(self, environ, book_id):
        book = self.store.get_book(_parse_id(book_id))
        if book is None:
            raise HttpError(404, "book not found")
        return 200, book, ()

    def _create_book(self, environ):
        book = self.store.create_book(validate_book(_read_json(environ)))
        return 201, book, [("Location", f"/books/{book['id']}")]

    def _update_book(self, environ, book_id):
        book_id = _parse_id(book_id)
        data = validate_book(_read_json(environ))
        book = self.store.update_book(book_id, data)
        if book is None:
            raise HttpError(404, "book not found")
        return 200, book, ()

    def _delete_book(self, environ, book_id):
        if not self.store.delete_book(_parse_id(book_id)):
            raise HttpError(404, "book not found")
        return 204, None, ()


def _match_route(path):
    if len(path) > 1:
        path = path.rstrip("/")
    for pattern, handlers in ROUTES:
        match = pattern.fullmatch(path)
        if match:
            return handlers, match.groupdict()
    raise HttpError(404, "route not found")


def _parse_id(raw):
    if not re.fullmatch(r"[0-9]+", raw):
        raise HttpError(400, "book id must be an integer")
    book_id = int(raw)
    if book_id > MAX_BOOK_ID:
        raise HttpError(404, "book not found")
    return book_id


def _read_json(environ):
    media_type = environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise HttpError(415, "Content-Type must be application/json")
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise HttpError(400, "invalid Content-Length") from None
    if length < 0:
        raise HttpError(400, "invalid Content-Length")
    if length > MAX_BODY_BYTES:
        raise HttpError(413, f"request body must be at most {MAX_BODY_BYTES} bytes")
    raw = environ["wsgi.input"].read(length)
    try:
        return json.loads(raw)
    except ValueError:  # includes JSONDecodeError and UnicodeDecodeError
        raise HttpError(400, "request body is not valid JSON") from None


def _json(code, payload=None, extra_headers=()):
    status = f"{code} {HTTPStatus(code).phrase}"
    headers = []
    if payload is None:
        body = b""
    else:
        body = json.dumps(payload).encode("utf-8")
        headers.append(("Content-Type", JSON_CONTENT_TYPE))
    headers.extend(extra_headers)
    headers.append(("Content-Length", str(len(body))))
    return status, headers, body
