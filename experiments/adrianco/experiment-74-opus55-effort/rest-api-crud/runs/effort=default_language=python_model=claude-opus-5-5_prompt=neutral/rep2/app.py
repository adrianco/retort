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

FIELDS = ("title", "author", "year", "isbn")
REQUIRED = ("title", "author")
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """SQLite-backed book repository."""

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

    def close(self):
        self._conn.close()

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                tuple(data.get(f) for f in FIELDS),
            )
            book_id = cur.lastrowid
        return self.get(book_id)

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

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return dict(row) if row else None

    def update(self, book_id, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (*(data.get(f) for f in FIELDS), book_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0


def validate_book(payload):
    """Validate and normalise a book payload. Raises ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    unknown = set(payload) - set(FIELDS) - {"id"}
    if unknown:
        errors["unknown_fields"] = sorted(unknown)

    clean = {}
    for field in REQUIRED:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            clean[field] = value.strip()

    year = payload.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "must be an integer"
        elif not -5000 <= year <= 9999:
            errors["year"] = "must be between -5000 and 9999"
        else:
            clean["year"] = year

    isbn = payload.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            errors["isbn"] = "must be a string"
        else:
            digits = isbn.replace("-", "").replace(" ", "")
            if not re.fullmatch(r"\d{9}[\dXx]|\d{13}", digits):
                errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
            else:
                clean["isbn"] = isbn.strip()

    if errors:
        raise ValidationError(errors)
    return clean


class BookHandler(BaseHTTPRequestHandler):
    store: BookStore = None  # injected by make_server
    server_version = "BookAPI/1.0"

    def log_message(self, fmt, *args):
        if os.environ.get("BOOKAPI_QUIET") != "1":
            super().log_message(fmt, *args)

    # -- helpers ---------------------------------------------------------
    def _send(self, status, body=None):
        payload = b"" if body is None else json.dumps(body).encode()
        self.send_response(status)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _error(self, status, message, details=None):
        body = {"error": message}
        if details:
            body["details"] = details
        self._send(status, body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw or b"null")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _INVALID

    def _book_id(self, path):
        match = BOOK_PATH.match(path)
        return int(match.group(1)) if match else None

    def _not_found(self):
        self._error(HTTPStatus.NOT_FOUND, "not found")

    # -- verbs -----------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        if path == "/health":
            try:
                self.store.ping()
            except sqlite3.Error:
                return self._send(
                    HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "database": "down"}
                )
            return self._send(HTTPStatus.OK, {"status": "ok", "database": "ok"})
        if path == "/books":
            author = parse_qs(url.query).get("author", [None])[0]
            return self._send(HTTPStatus.OK, self.store.list(author))
        book_id = self._book_id(path)
        if book_id is None:
            return self._not_found()
        book = self.store.get(book_id)
        if book is None:
            return self._error(HTTPStatus.NOT_FOUND, f"book {book_id} not found")
        self._send(HTTPStatus.OK, book)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        if path != "/books":
            if self._book_id(path) is not None:
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            return self._not_found()
        data = self._validated_body()
        if data is None:
            return
        book = self.store.create(data)
        self.send_response(HTTPStatus.CREATED)
        body = json.dumps(book).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Location", f"/books/{book['id']}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        path = urlparse(self.path).path.rstrip("/")
        book_id = self._book_id(path)
        if book_id is None:
            if path == "/books":
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            return self._not_found()
        data = self._validated_body()
        if data is None:
            return
        book = self.store.update(book_id, data)
        if book is None:
            return self._error(HTTPStatus.NOT_FOUND, f"book {book_id} not found")
        self._send(HTTPStatus.OK, book)

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        book_id = self._book_id(path)
        if book_id is None:
            if path == "/books":
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            return self._not_found()
        if not self.store.delete(book_id):
            return self._error(HTTPStatus.NOT_FOUND, f"book {book_id} not found")
        self._send(HTTPStatus.NO_CONTENT)

    def _validated_body(self):
        payload = self._read_json()
        if payload is _INVALID:
            self._error(HTTPStatus.BAD_REQUEST, "invalid JSON body")
            return None
        try:
            return validate_book(payload)
        except ValidationError as exc:
            self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "validation failed", exc.errors)
            return None


_INVALID = object()


def make_server(host="127.0.0.1", port=8000, db_path="books.db"):
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
