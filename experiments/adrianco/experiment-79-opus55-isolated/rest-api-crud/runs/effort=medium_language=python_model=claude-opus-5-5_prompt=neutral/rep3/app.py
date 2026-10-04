"""Book collection REST API.

A dependency-free WSGI application backed by SQLite. Run with:

    python app.py [--host HOST] [--port PORT] [--db PATH]
"""

import argparse
import json
import os
import re
import sqlite3
import threading
import traceback
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, make_server

DEFAULT_DB_PATH = "books.db"
MAX_BODY_BYTES = 1024 * 1024
MAX_YEAR = 9999

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
)
"""

BOOK_PATH = re.compile(r"^/books/([^/]+)$")


class ApiError(Exception):
    """An error that maps directly onto a JSON HTTP response."""

    def __init__(self, status, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []


class BookStore:
    """SQLite persistence for books.

    A single connection is shared and guarded by a lock so the store is safe
    to use from a threaded server and works with ":memory:" databases.
    """

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.execute(SCHEMA)

    def close(self):
        with self._lock:
            self._conn.close()

    def create(self, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            return self._get(cur.lastrowid)

    def list(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        with self._lock:
            rows = self._conn.execute(query + " ORDER BY id", params).fetchall()
        return [dict(row) for row in rows]

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def update(self, book_id, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            if cur.rowcount == 0:
                return None
            return self._get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def _get(self, book_id):
        row = self._conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None


def validate_book(payload):
    """Return a normalised book dict, or raise a 400 ApiError listing problems."""
    if not isinstance(payload, dict):
        raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")

    errors = {}
    book = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if value is None:
            errors[field] = f"{field} is required"
        elif not isinstance(value, str) or not value.strip():
            errors[field] = f"{field} must be a non-empty string"
        else:
            book[field] = value.strip()

    year = payload.get("year")
    # bool is a subclass of int, so exclude it explicitly.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "year must be an integer"
    elif year is not None and abs(year) > MAX_YEAR:
        errors["year"] = f"year must be between -{MAX_YEAR} and {MAX_YEAR}"
    book["year"] = year

    isbn = payload.get("isbn")
    if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
        errors["isbn"] = "isbn must be a non-empty string"
    else:
        book["isbn"] = isbn.strip() if isbn is not None else None

    if errors:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Validation failed", details=errors)
    return book


def read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
    if length < 0:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
    if length > MAX_BODY_BYTES:
        raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body too large")
    raw = environ["wsgi.input"].read(length) if length else b""
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ApiError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON")


def parse_query(environ):
    return parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)


def parse_book_id(raw):
    # Anything that is not a plain positive integer cannot name a book; the
    # length cap keeps the value within SQLite's 64-bit integer range.
    if not raw.isascii() or not raw.isdigit() or len(raw) > 18:
        raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
    return int(raw)


def method_not_allowed(allowed):
    return ApiError(
        HTTPStatus.METHOD_NOT_ALLOWED,
        "Method not allowed",
        headers=[("Allow", ", ".join(allowed))],
    )


def create_app(db_path=DEFAULT_DB_PATH):
    """Build the WSGI application. The store is exposed as ``app.store``."""
    store = BookStore(db_path)

    def save(operation):
        try:
            return operation()
        except sqlite3.IntegrityError:
            raise ApiError(HTTPStatus.CONFLICT, "A book with this isbn already exists")

    def route(environ):
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO", "") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            if method != "GET":
                raise method_not_allowed(["GET"])
            return HTTPStatus.OK, {"status": "ok"}, []

        if path == "/books":
            if method == "GET":
                authors = parse_query(environ).get("author")
                return HTTPStatus.OK, store.list(authors[0] if authors else None), []
            if method == "POST":
                book = validate_book(read_json(environ))
                created = save(lambda: store.create(book))
                headers = [("Location", f"/books/{created['id']}")]
                return HTTPStatus.CREATED, created, headers
            raise method_not_allowed(["GET", "POST"])

        match = BOOK_PATH.match(path)
        if match:
            if method not in ("GET", "PUT", "DELETE"):
                raise method_not_allowed(["GET", "PUT", "DELETE"])
            book_id = parse_book_id(match.group(1))
            if method == "GET":
                found = store.get(book_id)
            elif method == "PUT":
                book = validate_book(read_json(environ))
                found = save(lambda: store.update(book_id, book))
            else:
                if store.delete(book_id):
                    return HTTPStatus.NO_CONTENT, None, []
                found = None
            if found is None:
                raise ApiError(HTTPStatus.NOT_FOUND, "Book not found")
            return HTTPStatus.OK, found, []

        raise ApiError(HTTPStatus.NOT_FOUND, "Not found")

    def app(environ, start_response):
        try:
            status, payload, headers = route(environ)
        except ApiError as exc:
            status, headers = exc.status, exc.headers
            payload = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
        except Exception:
            environ["wsgi.errors"].write("Unhandled error while serving request\n")
            traceback.print_exc(file=environ["wsgi.errors"])
            status, headers = HTTPStatus.INTERNAL_SERVER_ERROR, []
            payload = {"error": "Internal server error"}

        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        response_headers = list(headers)
        if payload is not None:
            response_headers.append(("Content-Type", "application/json"))
        response_headers.append(("Content-Length", str(len(body))))
        start_response(f"{status.value} {status.phrase}", response_headers)
        return [body]

    app.store = store
    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", DEFAULT_DB_PATH))
    args = parser.parse_args(argv)

    app = create_app(args.db)
    with make_server(args.host, args.port, app, handler_class=WSGIRequestHandler) as server:
        print(f"Serving on http://{args.host}:{server.server_port} (db: {args.db})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            app.store.close()


if __name__ == "__main__":
    main()
