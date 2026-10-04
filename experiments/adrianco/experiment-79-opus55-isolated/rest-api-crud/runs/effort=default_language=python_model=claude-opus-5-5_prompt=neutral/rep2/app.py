"""REST API for managing a book collection.

A dependency-free WSGI application (standard library only) backed by SQLite.
Run with `python app.py`.
"""

import json
import os
import re
import traceback
from http import HTTPStatus
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from db import BookStore, DuplicateISBN

MAX_BODY_BYTES = 1024 * 1024
# 18 digits keeps ids inside SQLite's signed 64-bit integer range.
BOOK_PATH = re.compile(r"^/books/(\d{1,18})$")


class HTTPError(Exception):
    def __init__(self, status, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []


def validate_book(data):
    """Validate a book payload and return it in normalized form."""
    if not isinstance(data, dict):
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")

    errors = {}
    book = {}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors[field] = f"{field} is required"
        elif not isinstance(value, str):
            errors[field] = f"{field} must be a string"
        elif not value.strip():
            errors[field] = f"{field} must not be empty"
        else:
            book[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, but true/false is not a year.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "year must be an integer"
    book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"
    else:
        # A blank ISBN is treated as "not provided".
        book["isbn"] = (isbn.strip() or None) if isbn else None

    if errors:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Validation failed", details=errors)
    return book


def read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
    if length < 0:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
    if length > MAX_BODY_BYTES:
        raise HTTPError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body is too large")
    body = environ["wsgi.input"].read(length) if length else b""
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON")


def method_not_allowed(*allowed):
    return HTTPError(
        HTTPStatus.METHOD_NOT_ALLOWED,
        "Method not allowed",
        headers=[("Allow", ", ".join(allowed))],
    )


class BookAPI:
    """WSGI application exposing the book collection."""

    def __init__(self, db_path="books.db"):
        self.store = BookStore(db_path)

    def __call__(self, environ, start_response):
        try:
            status, payload, headers = self.dispatch(environ)
        except HTTPError as exc:
            status, headers = exc.status, exc.headers
            payload = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
        except Exception:
            environ["wsgi.errors"].write(traceback.format_exc())
            status, headers = HTTPStatus.INTERNAL_SERVER_ERROR, []
            payload = {"error": "Internal server error"}

        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = list(headers) + [("Content-Length", str(len(body)))]
        if payload is not None:
            headers.append(("Content-Type", "application/json"))
        start_response(f"{status.value} {status.phrase}", headers)
        return [body]

    def dispatch(self, environ):
        """Route a request. Returns (status, json payload or None, headers)."""
        method = environ["REQUEST_METHOD"]
        # WSGI hands over the path as latin-1 decoded bytes.
        path = environ.get("PATH_INFO", "").encode("latin-1").decode("utf-8", "replace")
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            if method != "GET":
                raise method_not_allowed("GET")
            return HTTPStatus.OK, {"status": "ok"}, []

        if path == "/books":
            if method == "GET":
                query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
                author = query["author"][0] if "author" in query else None
                return HTTPStatus.OK, self.store.list(author=author), []
            if method == "POST":
                book = validate_book(read_json(environ))
                try:
                    created = self.store.create(book)
                except DuplicateISBN:
                    raise isbn_conflict(book["isbn"])
                location = [("Location", f"/books/{created['id']}")]
                return HTTPStatus.CREATED, created, location
            raise method_not_allowed("GET", "POST")

        match = BOOK_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = self.store.get(book_id)
                if book is None:
                    raise book_not_found(book_id)
                return HTTPStatus.OK, book, []
            if method == "PUT":
                book = validate_book(read_json(environ))
                try:
                    updated = self.store.update(book_id, book)
                except DuplicateISBN:
                    raise isbn_conflict(book["isbn"])
                if updated is None:
                    raise book_not_found(book_id)
                return HTTPStatus.OK, updated, []
            if method == "DELETE":
                if not self.store.delete(book_id):
                    raise book_not_found(book_id)
                return HTTPStatus.NO_CONTENT, None, []
            raise method_not_allowed("GET", "PUT", "DELETE")

        raise HTTPError(HTTPStatus.NOT_FOUND, "Not found")


def book_not_found(book_id):
    return HTTPError(HTTPStatus.NOT_FOUND, f"Book {book_id} not found")


def isbn_conflict(isbn):
    return HTTPError(HTTPStatus.CONFLICT, f"A book with isbn {isbn!r} already exists")


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", "books.db")
    app = BookAPI(db_path)
    with make_server(
        host, port, app, server_class=ThreadingWSGIServer, handler_class=WSGIRequestHandler
    ) as server:
        print(f"Serving on http://{host}:{port} (database: {db_path})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
