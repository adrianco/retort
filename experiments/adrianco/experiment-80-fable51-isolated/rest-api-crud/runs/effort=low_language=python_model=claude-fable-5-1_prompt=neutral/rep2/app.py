"""Book collection REST API using only the Python standard library and SQLite."""

import json
import os
import re
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIELDS = ("title", "author", "year", "isbn")
MAX_BODY = 1_000_000
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    pass


class BookStore:
    """SQLite-backed storage for books."""

    def __init__(self, path=":memory:"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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

    def create(self, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                [book[f] for f in FIELDS],
            )
            return self._get(cur.lastrowid)

    def list(self, author=None):
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id")
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                )
            return [dict(r) for r in rows]

    def _get(self, book_id):
        row = self._conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def update(self, book_id, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                [book[f] for f in FIELDS] + [book_id],
            )
            return self._get(book_id) if cur.rowcount else None

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def close(self):
        self._conn.close()


def validate_book(data):
    """Validate a request payload and return a normalized book dict."""
    if not isinstance(data, dict):
        raise ValidationError("request body must be a JSON object")
    errors = []
    book = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} is required and must be a non-empty string")
        else:
            book[field] = value.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    book["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    book["isbn"] = isbn
    if errors:
        raise ValidationError("; ".join(errors))
    return book


class BookHandler(BaseHTTPRequestHandler):
    store = None  # set by make_server
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # keep test output quiet
        if os.environ.get("BOOKS_LOG"):
            super().log_message(format, *args)

    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message):
        self._send(status, {"error": message})

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValidationError("invalid Content-Length")
        if length < 0 or length > MAX_BODY:
            self.close_connection = True
            raise ValidationError("request body too large")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ValidationError("request body must be valid JSON")

    def _route(self, method):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        try:
            if path == "/health":
                if method != "GET":
                    return self._error(405, "method not allowed")
                return self._send(200, {"status": "ok"})
            if path == "/books":
                if method == "GET":
                    author = parse_qs(url.query).get("author", [None])[0]
                    return self._send(200, self.store.list(author))
                if method == "POST":
                    book = validate_book(self._read_json())
                    return self._send(201, self.store.create(book))
                return self._error(405, "method not allowed")
            match = BOOK_PATH.match(path)
            if match:
                book_id = int(match.group(1))
                if method == "GET":
                    book = self.store.get(book_id)
                elif method == "PUT":
                    book = self.store.update(book_id, validate_book(self._read_json()))
                elif method == "DELETE":
                    if self.store.delete(book_id):
                        return self._send(204)
                    book = None
                else:
                    return self._error(405, "method not allowed")
                if book is None:
                    return self._error(404, "book not found")
                return self._send(200, book)
            return self._error(404, "not found")
        except ValidationError as exc:
            return self._error(400, str(exc))
        except Exception:
            return self._error(500, "internal server error")

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")


def make_server(host="127.0.0.1", port=8000, db_path="books.db"):
    store = BookStore(db_path)
    handler = type("Handler", (BookHandler,), {"store": store})
    return ThreadingHTTPServer((host, port), handler)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", "books.db")
    os.environ.setdefault("BOOKS_LOG", "1")
    server = make_server(host, port, db_path)
    print(f"Listening on http://{host}:{port} (db: {db_path})", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
