"""REST API for managing a book collection.

Built on the Python standard library only: a WSGI application served by
``wsgiref`` with SQLite for storage.
"""

import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, make_server

DEFAULT_DB_PATH = "books.db"
MAX_BODY_BYTES = 1024 * 1024
MAX_YEAR = 9999

BOOK_PATH = re.compile(r"^/books/([^/]+)$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


class ApiError(Exception):
    """An error that maps directly onto a JSON error response."""

    def __init__(self, status, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []


def validate_book(data):
    """Return a cleaned book dict, or raise a 400 ApiError listing every problem."""
    if not isinstance(data, dict):
        raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")

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
    # bool is a subclass of int, so it has to be rejected explicitly.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "year must be an integer"
    elif year is not None and abs(year) > MAX_YEAR:
        errors["year"] = f"year must be between -{MAX_YEAR} and {MAX_YEAR}"
    book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"
    else:
        # A blank isbn is stored as "no isbn".
        book["isbn"] = (isbn.strip() or None) if isbn else None

    if errors:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Validation failed", errors)
    return book


class BookStore:
    """SQLite-backed storage. A connection is opened per operation, so one
    instance can be shared safely between threads."""

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        with closing(self._connect()) as conn, conn:
            conn.execute(SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, book):
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            return self._get(conn, cursor.lastrowid)

    def list(self, author=None):
        query = "SELECT * FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        with closing(self._connect()) as conn:
            rows = conn.execute(query + " ORDER BY id", params).fetchall()
        return [dict(row) for row in rows]

    def get(self, book_id):
        with closing(self._connect()) as conn:
            return self._get(conn, book_id)

    def update(self, book_id, book):
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            if cursor.rowcount == 0:
                return None
            return self._get(conn, book_id)

    def delete(self, book_id):
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _get(conn, book_id):
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None


def read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
    if length < 0:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
    if length > MAX_BODY_BYTES:
        raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body is too large")
    if length == 0:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")
    try:
        return json.loads(environ["wsgi.input"].read(length))
    except (ValueError, RecursionError):
        raise ApiError(HTTPStatus.BAD_REQUEST, "Request body is not valid JSON")


def query_param(environ, name):
    """First value of a query-string parameter, or None when it is absent."""
    values = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True).get(name)
    return values[0] if values else None


def parse_book_id(raw):
    # IDs are positive integers; anything else cannot name an existing book.
    # The length cap keeps the value inside SQLite's 64-bit integer range.
    if not raw.isascii() or not raw.isdigit() or len(raw) > 18:
        raise not_found()
    return int(raw)


def not_found():
    return ApiError(HTTPStatus.NOT_FOUND, "Book not found")


def method_not_allowed(*allowed):
    return ApiError(
        HTTPStatus.METHOD_NOT_ALLOWED,
        "Method not allowed",
        headers=[("Allow", ", ".join(allowed))],
    )


def create_app(db_path=DEFAULT_DB_PATH):
    """Build the WSGI application backed by the SQLite database at ``db_path``."""
    store = BookStore(db_path)

    def route(environ):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "")
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            if method != "GET":
                raise method_not_allowed("GET")
            return HTTPStatus.OK, {"status": "ok"}

        if path == "/books":
            if method == "GET":
                return HTTPStatus.OK, store.list(query_param(environ, "author"))
            if method == "POST":
                book = store.create(validate_book(read_json(environ)))
                return HTTPStatus.CREATED, book
            raise method_not_allowed("GET", "POST")

        match = BOOK_PATH.match(path)
        if match:
            if method not in ("GET", "PUT", "DELETE"):
                raise method_not_allowed("GET", "PUT", "DELETE")
            book_id = parse_book_id(match.group(1))
            if method == "GET":
                book = store.get(book_id)
            elif method == "PUT":
                book = store.update(book_id, validate_book(read_json(environ)))
            else:
                if not store.delete(book_id):
                    raise not_found()
                return HTTPStatus.NO_CONTENT, None
            if book is None:
                raise not_found()
            return HTTPStatus.OK, book

        raise ApiError(HTTPStatus.NOT_FOUND, "Not found")

    def app(environ, start_response):
        headers = []
        try:
            status, payload = route(environ)
        except ApiError as exc:
            status = exc.status
            payload = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
            headers = list(exc.headers)
        except Exception:
            environ["wsgi.errors"].write(f"Unhandled error: {sys.exc_info()[1]!r}\n")
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            payload = {"error": "Internal server error"}

        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        if payload is not None:
            headers.append(("Content-Type", "application/json"))
        headers.append(("Content-Length", str(len(body))))
        start_response(f"{status.value} {status.phrase}", headers)
        return [body]

    return app


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    with make_server(host, port, create_app(db_path)) as server:
        print(f"Serving on http://{host}:{port} (database: {db_path})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down")


class QuietHandler(WSGIRequestHandler):
    """Request handler that does not log each request; used by the tests."""

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    main()
