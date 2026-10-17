"""WSGI application exposing the book collection as a JSON REST API."""

import json
import logging
import os
import re
import sqlite3
from http import HTTPStatus
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIServer, make_server

from .db import BookStore, DuplicateISBNError
from .validation import ValidationError, parse_book

MAX_BODY_BYTES = 64 * 1024
MAX_ID = 2**63 - 1  # SQLite INTEGER limit
BOOK_PATH = re.compile(r"/books/([0-9]+)")

logger = logging.getLogger(__name__)


class RequestError(Exception):
    def __init__(self, status, message, details=None, headers=()):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = list(headers)


class BooksApp:
    def __init__(self, store):
        self.store = store

    def __call__(self, environ, start_response):
        try:
            status, payload, headers = self.route(environ)
        except RequestError as exc:
            status, headers = exc.status, exc.headers
            payload = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
        except Exception:
            logger.exception("unhandled error")
            status, headers = HTTPStatus.INTERNAL_SERVER_ERROR, []
            payload = {"error": "internal server error"}

        body = b""
        if payload is not None:
            body = json.dumps(payload).encode()
            headers = [("Content-Type", "application/json")] + headers
        headers = [("Content-Length", str(len(body)))] + headers
        start_response(f"{status.value} {status.phrase}", headers)
        return [body]

    def route(self, environ):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "")

        if path == "/health":
            return self._health(method)

        if path == "/books":
            if method == "GET":
                return self._list(environ)
            if method == "POST":
                return self._create(environ)
            raise _method_not_allowed("GET, POST")

        match = BOOK_PATH.fullmatch(path)
        if match:
            book_id = int(match.group(1))
            if book_id > MAX_ID:
                raise RequestError(HTTPStatus.NOT_FOUND, "book not found")
            if method == "GET":
                return self._get(book_id)
            if method == "PUT":
                return self._update(environ, book_id)
            if method == "DELETE":
                return self._delete(book_id)
            raise _method_not_allowed("GET, PUT, DELETE")

        raise RequestError(HTTPStatus.NOT_FOUND, "not found")

    def _health(self, method):
        if method != "GET":
            raise _method_not_allowed("GET")
        try:
            self.store.ping()
        except sqlite3.Error:
            return HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable"}, []
        return HTTPStatus.OK, {"status": "ok"}, []

    def _list(self, environ):
        query = parse_qs(environ.get("QUERY_STRING", ""))
        author = query.get("author", [""])[0].strip()
        books = self.store.list_books(author or None)
        return HTTPStatus.OK, books, []

    def _create(self, environ):
        data = _parse_book_body(environ)
        try:
            book = self.store.create(data)
        except DuplicateISBNError:
            raise _duplicate_isbn()
        return HTTPStatus.CREATED, book, [("Location", f"/books/{book['id']}")]

    def _get(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            raise RequestError(HTTPStatus.NOT_FOUND, "book not found")
        return HTTPStatus.OK, book, []

    def _update(self, environ, book_id):
        data = _parse_book_body(environ)
        try:
            book = self.store.update(book_id, data)
        except DuplicateISBNError:
            raise _duplicate_isbn()
        if book is None:
            raise RequestError(HTTPStatus.NOT_FOUND, "book not found")
        return HTTPStatus.OK, book, []

    def _delete(self, book_id):
        if not self.store.delete(book_id):
            raise RequestError(HTTPStatus.NOT_FOUND, "book not found")
        return HTTPStatus.NO_CONTENT, None, []


def _parse_book_body(environ):
    try:
        return parse_book(_read_json(environ))
    except ValidationError as exc:
        raise RequestError(HTTPStatus.BAD_REQUEST, "validation failed", exc.errors)


def _read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise RequestError(HTTPStatus.BAD_REQUEST, "invalid Content-Length header")
    if length < 0:
        raise RequestError(HTTPStatus.BAD_REQUEST, "invalid Content-Length header")
    if length > MAX_BODY_BYTES:
        raise RequestError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")

    raw = environ["wsgi.input"].read(length) if length else b""
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RequestError(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")


def _method_not_allowed(allow):
    return RequestError(
        HTTPStatus.METHOD_NOT_ALLOWED,
        "method not allowed",
        headers=[("Allow", allow)],
    )


def _duplicate_isbn():
    return RequestError(HTTPStatus.CONFLICT, "a book with this ISBN already exists")


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def make_books_server(app, host="127.0.0.1", port=0):
    return make_server(host, port, app, server_class=_ThreadingWSGIServer)


def create_app(db_path=None):
    store = BookStore(db_path or os.environ.get("BOOKS_DB_PATH", "books.db"))
    return BooksApp(store)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    with make_books_server(app, host, port) as server:
        print(f"Serving books API on http://{host}:{server.server_port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
