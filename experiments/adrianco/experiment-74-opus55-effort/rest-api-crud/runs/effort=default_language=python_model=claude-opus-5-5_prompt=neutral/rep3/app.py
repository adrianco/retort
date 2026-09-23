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
from urllib.parse import parse_qs, urlparse

MAX_BODY_BYTES = 1_000_000
FIELDS = ("title", "author", "year", "isbn")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """SQLite-backed storage for books."""

    def __init__(self, db_path=":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )"""
            )

    @staticmethod
    def _to_dict(row):
        return dict(row) if row else None

    def create(self, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book.get("year"), book.get("isbn")),
            )
            return self._get(cur.lastrowid)

    def list(self, author=None):
        with self._lock:
            if author:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def _get(self, book_id):
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._to_dict(row)

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def update(self, book_id, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book.get("year"), book.get("isbn"), book_id),
            )
            if cur.rowcount == 0:
                return None
            return self._get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def close(self):
        self._conn.close()


def validate_book(data):
    """Validate a book payload and return a normalised dict.

    title and author are required non-empty strings; year is an optional
    integer; isbn is an optional string. Unknown fields are rejected.
    """
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        errors["unknown_fields"] = f"unexpected fields: {', '.join(unknown)}"

    book = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = f"{field} is required and must be a non-empty string"
        else:
            book[field] = value.strip()

    year = data.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "year must be an integer"
        elif not -9999 <= year <= 9999:
            errors["year"] = "year must be between -9999 and 9999"
        else:
            book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            errors["isbn"] = "isbn must be a string"
        else:
            cleaned = isbn.replace("-", "").replace(" ", "")
            if not re.fullmatch(r"\d{9}[\dXx]|\d{13}", cleaned):
                errors["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13"
            else:
                book["isbn"] = isbn.strip()

    if errors:
        raise ValidationError(errors)
    return book


BOOK_PATH = re.compile(r"^/books/([^/]+)/?$")


class BookHandler(BaseHTTPRequestHandler):
    store: BookStore = None  # set by make_server
    server_version = "BookAPI/1.0"

    # --- helpers -----------------------------------------------------------
    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _error(self, status, message, details=None):
        payload = {"error": message}
        if details:
            payload["details"] = details
        self._send(status, payload)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            self._error(HTTPStatus.BAD_REQUEST, "invalid Content-Length")
            return None, False
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8")), True
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")
            return None, False

    def _book_id(self, path):
        match = BOOK_PATH.match(path)
        if not match:
            return None, False
        raw = match.group(1)
        if not raw.isdigit():
            self._error(HTTPStatus.BAD_REQUEST, "book id must be a positive integer")
            return None, True
        return int(raw), True

    def log_message(self, fmt, *args):  # keep test output quiet unless enabled
        if os.environ.get("BOOKS_API_LOG"):
            super().log_message(fmt, *args)

    # --- routing ------------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            return self._send(HTTPStatus.OK, {"status": "ok"})
        if path in ("/books", "/books/"):
            author = parse_qs(parsed.query).get("author", [None])[0]
            return self._send(HTTPStatus.OK, self.store.list(author=author))
        book_id, matched = self._book_id(path)
        if not matched:
            return self._error(HTTPStatus.NOT_FOUND, "not found")
        if book_id is None:
            return
        book = self.store.get(book_id)
        if book is None:
            return self._error(HTTPStatus.NOT_FOUND, "book not found")
        self._send(HTTPStatus.OK, book)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/books", "/books/"):
            if BOOK_PATH.match(path):
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            return self._error(HTTPStatus.NOT_FOUND, "not found")
        data, ok = self._read_json()
        if not ok:
            return
        try:
            book = validate_book(data)
        except ValidationError as exc:
            return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "validation failed", exc.errors)
        self._send_created(self.store.create(book))

    def _send_created(self, book):
        body = json.dumps(book).encode("utf-8")
        self.send_response(HTTPStatus.CREATED)
        self.send_header("Content-Type", "application/json")
        self.send_header("Location", f"/books/{book['id']}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        path = urlparse(self.path).path
        book_id, matched = self._book_id(path)
        if not matched:
            if path in ("/books", "/books/"):
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            return self._error(HTTPStatus.NOT_FOUND, "not found")
        if book_id is None:
            return
        data, ok = self._read_json()
        if not ok:
            return
        try:
            book = validate_book(data)
        except ValidationError as exc:
            return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "validation failed", exc.errors)
        updated = self.store.update(book_id, book)
        if updated is None:
            return self._error(HTTPStatus.NOT_FOUND, "book not found")
        self._send(HTTPStatus.OK, updated)

    def do_DELETE(self):
        path = urlparse(self.path).path
        book_id, matched = self._book_id(path)
        if not matched:
            if path in ("/books", "/books/"):
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            return self._error(HTTPStatus.NOT_FOUND, "not found")
        if book_id is None:
            return
        if not self.store.delete(book_id):
            return self._error(HTTPStatus.NOT_FOUND, "book not found")
        self._send(HTTPStatus.NO_CONTENT)


def make_server(host="127.0.0.1", port=8000, db_path="books.db"):
    """Build a server bound to its own BookStore (handler subclass per server)."""
    store = BookStore(db_path)
    handler = type("BoundBookHandler", (BookHandler,), {"store": store})
    server = ThreadingHTTPServer((host, port), handler)
    server.store = store
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", "books.db")
    server = make_server(host, port, db_path)
    print(f"Book API listening on http://{host}:{port} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
