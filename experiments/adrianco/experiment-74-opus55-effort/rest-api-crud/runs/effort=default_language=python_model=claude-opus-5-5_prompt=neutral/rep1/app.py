"""Book collection REST API using only the Python standard library.

Endpoints:
    GET    /health
    POST   /books
    GET    /books[?author=...]
    GET    /books/{id}
    PUT    /books/{id}
    DELETE /books/{id}
"""

import json
import os
import re
import sqlite3
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

FIELDS = ("title", "author", "year", "isbn")
MAX_BODY_BYTES = 1_000_000
BOOK_PATH = re.compile(r"^/books/([^/]+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """SQLite-backed storage for books. Thread-safe via a single lock."""

    def __init__(self, db_path=":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year   INTEGER,
                    isbn   TEXT
                )"""
            )

    @staticmethod
    def _to_dict(row):
        return dict(row) if row is not None else None

    def create(self, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                tuple(book.get(f) for f in FIELDS),
            )
            new_id = cur.lastrowid
        return self.get(new_id)

    def list(self, author=None):
        with self._lock:
            if author is not None:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [self._to_dict(r) for r in rows]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return self._to_dict(row)

    def update(self, book_id, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (*(book.get(f) for f in FIELDS), book_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def close(self):
        self._conn.close()


def validate_book(data):
    """Validate and normalise a book payload. Raises ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    clean = {}

    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            clean[field] = value.strip()

    year = data.get("year")
    if year is not None:
        # bool is a subclass of int; reject it explicitly.
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "must be an integer"
        elif not -5000 <= year <= 9999:
            errors["year"] = "must be between -5000 and 9999"
        else:
            clean["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            errors["isbn"] = "must be a string"
        else:
            digits = isbn.replace("-", "").replace(" ", "")
            if not (
                (len(digits) == 10 and digits[:9].isdigit() and (digits[9].isdigit() or digits[9] in "xX"))
                or (len(digits) == 13 and digits.isdigit())
            ):
                errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
            else:
                clean["isbn"] = isbn.strip()

    unknown = set(data) - set(FIELDS) - {"id"}
    if unknown:
        errors["unknown_fields"] = sorted(unknown)

    if errors:
        raise ValidationError(errors)
    return clean


def handle_request(store, method, raw_path, body=b""):
    """Route a request. Returns (HTTPStatus, payload-or-None)."""
    parts = urlsplit(raw_path)
    path = parts.path.rstrip("/") or "/"
    query = parse_qs(parts.query)

    def parse_body():
        try:
            return json.loads(body or b"")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValidationError({"body": "must be valid JSON"})

    try:
        if path == "/health":
            if method != "GET":
                return _method_not_allowed()
            try:
                store.ping()
            except sqlite3.Error:
                return HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "database": "unavailable"}
            return HTTPStatus.OK, {"status": "ok", "database": "ok"}

        if path == "/books":
            if method == "GET":
                author = query.get("author", [None])[0]
                return HTTPStatus.OK, store.list(author=author)
            if method == "POST":
                book = validate_book(parse_body())
                return HTTPStatus.CREATED, store.create(book)
            return _method_not_allowed()

        match = BOOK_PATH.match(path)
        if match:
            raw_id = match.group(1)
            if not raw_id.isdigit():
                return HTTPStatus.NOT_FOUND, {"error": "Book not found"}
            book_id = int(raw_id)
            if method == "GET":
                book = store.get(book_id)
            elif method == "PUT":
                book = store.update(book_id, validate_book(parse_body()))
            elif method == "DELETE":
                if store.delete(book_id):
                    return HTTPStatus.NO_CONTENT, None
                book = None
            else:
                return _method_not_allowed()
            if book is None:
                return HTTPStatus.NOT_FOUND, {"error": "Book not found"}
            return HTTPStatus.OK, book

        return HTTPStatus.NOT_FOUND, {"error": "Not found"}
    except ValidationError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": "Validation failed", "details": exc.errors}


def _method_not_allowed():
    return HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Method not allowed"}


class BookRequestHandler(BaseHTTPRequestHandler):
    store = None  # set by make_server
    server_version = "BookAPI/1.0"

    def _dispatch(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            self._send(HTTPStatus.BAD_REQUEST if length < 0 else HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                       {"error": "Invalid request body size"})
            return
        body = self.rfile.read(length) if length else b""
        try:
            status, payload = handle_request(self.store, self.command, self.path, body)
        except Exception:  # pragma: no cover - defensive
            self.log_error("Unhandled error processing %s %s", self.command, self.path)
            status, payload = HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"}
        self._send(status, payload)

    def _send(self, status, payload):
        self.send_response(status)
        if payload is None:
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        data = json.dumps(payload).encode("utf-8")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _dispatch

    def log_message(self, format, *args):
        if not os.environ.get("BOOKS_QUIET"):
            super().log_message(format, *args)


def make_server(host="127.0.0.1", port=8000, db_path="books.db"):
    store = BookStore(db_path)
    handler = type("Handler", (BookRequestHandler,), {"store": store})
    server = ThreadingHTTPServer((host, port), handler)
    server.store = store
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", "books.db")
    server = make_server(host, port, db_path)
    print(f"Book API listening on http://{host}:{server.server_address[1]} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
