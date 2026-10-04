"""WSGI application exposing the book collection over HTTP."""

import json
import re
import sqlite3
import traceback
from http import HTTPStatus
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIServer, make_server

from .store import BookStore
from .validation import ValidationError, validate_book

MAX_BODY_BYTES = 1024 * 1024
MAX_BOOK_ID = 2**63 - 1  # largest rowid SQLite can hold

BOOK_PATH = re.compile(r"/books/([0-9]+)")


class HTTPError(Exception):
    """An error that maps directly onto a JSON error response."""

    def __init__(self, status, message, details=None, headers=()):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = list(headers)

    def response(self):
        body = {"error": self.message}
        if self.details:
            body["details"] = self.details
        return self.status, body, self.headers


def _not_found(book_id):
    return HTTPError(HTTPStatus.NOT_FOUND, f"Book {book_id} not found")


def _read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = -1
    if length < 0:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
    if length > MAX_BODY_BYTES:
        raise HTTPError(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            f"Request body must not exceed {MAX_BODY_BYTES} bytes",
        )
    raw = environ["wsgi.input"].read(length) if length else b""
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON") from None


def _read_book(environ):
    try:
        return validate_book(_read_json(environ))
    except ValidationError as exc:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Validation failed", exc.errors) from None


class BookAPI:
    """WSGI callable routing requests to handlers backed by a ``BookStore``."""

    def __init__(self, store):
        self.store = store

    def __call__(self, environ, start_response):
        try:
            status, body, headers = self._dispatch(environ)
        except HTTPError as exc:
            status, body, headers = exc.response()
        except Exception:
            traceback.print_exc(file=environ.get("wsgi.errors"))
            status, body, headers = (
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Internal server error"},
                [],
            )

        payload = b""
        headers = list(headers)
        if body is not None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers.append(("Content-Type", "application/json"))
            headers.append(("Content-Length", str(len(payload))))
        start_response(f"{status.value} {status.phrase}", headers)
        if environ["REQUEST_METHOD"] == "HEAD":
            return [b""]
        return [payload]

    def _dispatch(self, environ):
        path = environ.get("PATH_INFO", "").rstrip("/") or "/"
        args = ()
        if path == "/health":
            handlers = {"GET": self.health}
        elif path == "/books":
            handlers = {"GET": self.list_books, "POST": self.create_book}
        elif match := BOOK_PATH.fullmatch(path):
            digits = match.group(1).lstrip("0") or "0"
            # Check the length first: int() refuses absurdly long digit strings.
            if len(digits) > len(str(MAX_BOOK_ID)) or int(digits) > MAX_BOOK_ID:
                raise _not_found(digits)
            args = (int(digits),)
            handlers = {
                "GET": self.get_book,
                "PUT": self.update_book,
                "DELETE": self.delete_book,
            }
        else:
            raise HTTPError(HTTPStatus.NOT_FOUND, "Not found")

        # HEAD is answered like GET; __call__ drops the body.
        method = environ["REQUEST_METHOD"]
        handler = handlers.get("GET" if method == "HEAD" else method)
        if handler is None:
            raise HTTPError(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "Method not allowed",
                headers=[("Allow", ", ".join(handlers))],
            )
        return handler(environ, *args)

    def health(self, environ):
        try:
            self.store.ping()
        except sqlite3.Error:
            raise HTTPError(HTTPStatus.SERVICE_UNAVAILABLE, "Database unavailable") from None
        return HTTPStatus.OK, {"status": "ok"}, []

    def list_books(self, environ):
        query = parse_qs(environ.get("QUERY_STRING", ""))
        # parse_qs drops blank values, so `?author=` means "no filter".
        author = query["author"][0] if "author" in query else None
        return HTTPStatus.OK, self.store.list(author=author), []

    def create_book(self, environ):
        book = self.store.create(_read_book(environ))
        return HTTPStatus.CREATED, book, [("Location", f"/books/{book['id']}")]

    def get_book(self, environ, book_id):
        book = self.store.get(book_id)
        if book is None:
            raise _not_found(book_id)
        return HTTPStatus.OK, book, []

    def update_book(self, environ, book_id):
        book = self.store.update(book_id, _read_book(environ))
        if book is None:
            raise _not_found(book_id)
        return HTTPStatus.OK, book, []

    def delete_book(self, environ, book_id):
        if not self.store.delete(book_id):
            raise _not_found(book_id)
        return HTTPStatus.NO_CONTENT, None, []


def create_app(db_path=":memory:"):
    """Build the WSGI app with its own ``BookStore`` at ``db_path``."""
    return BookAPI(BookStore(db_path))


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def make_threaded_server(host, port, app):
    return make_server(host, port, app, server_class=ThreadingWSGIServer)
