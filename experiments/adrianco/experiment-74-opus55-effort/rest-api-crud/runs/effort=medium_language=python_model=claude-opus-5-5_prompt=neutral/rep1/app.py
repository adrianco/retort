"""Book collection REST API using only the Python standard library.

Endpoints:
    GET    /health
    POST   /books
    GET    /books[?author=...]
    GET    /books/{id}
    PUT    /books/{id}
    DELETE /books/{id}
"""

import argparse
import json
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIELDS = ("title", "author", "year", "isbn")
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """SQLite-backed storage for books. Thread-safe via a single lock."""

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
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
    def _row(row):
        return dict(row) if row else None

    def create(self, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                tuple(data.get(f) for f in FIELDS),
            )
            return self.get(cur.lastrowid, _locked=True)

    def list(self, author=None):
        with self._lock:
            if author:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                )
            else:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id")
            return [dict(r) for r in rows.fetchall()]

    def get(self, book_id, _locked=False):
        def fetch():
            return self._row(
                self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            )

        if _locked:
            return fetch()
        with self._lock:
            return fetch()

    def update(self, book_id, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (*(data.get(f) for f in FIELDS), book_id),
            )
            if cur.rowcount == 0:
                return None
            return self.get(book_id, _locked=True)

    def delete(self, book_id):
        with self._lock, self._conn:
            return self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,)).rowcount > 0

    def close(self):
        self._conn.close()


def validate_book(payload):
    """Validate and normalise a book payload. Returns a clean dict or raises ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    clean = {}
    for field in ("title", "author"):
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


def make_handler(store):
    class BookHandler(BaseHTTPRequestHandler):
        server_version = "BookAPI/1.0"

        def log_message(self, fmt, *args):  # keep test output quiet
            pass

        def _send(self, status, body=None):
            data = b"" if body is None else json.dumps(body).encode()
            self.send_response(status)
            if body is not None:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)

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
                raise ValidationError({"body": "invalid JSON"})

        def _book_id(self, path):
            m = BOOK_PATH.match(path)
            return int(m.group(1)) if m else None

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/health":
                return self._send(200, {"status": "ok"})
            if url.path == "/books":
                author = parse_qs(url.query).get("author", [None])[0]
                return self._send(200, store.list(author))
            book_id = self._book_id(url.path)
            if book_id is not None:
                book = store.get(book_id)
                return self._send(200, book) if book else self._error(404, "book not found")
            self._error(404, "not found")

        def do_POST(self):
            if urlparse(self.path).path != "/books":
                return self._error(404, "not found")
            try:
                data = validate_book(self._read_json())
            except ValidationError as e:
                return self._error(400, "validation failed", e.errors)
            self._send(201, store.create(data))

        def do_PUT(self):
            book_id = self._book_id(urlparse(self.path).path)
            if book_id is None:
                return self._error(404, "not found")
            try:
                data = validate_book(self._read_json())
            except ValidationError as e:
                return self._error(400, "validation failed", e.errors)
            book = store.update(book_id, data)
            self._send(200, book) if book else self._error(404, "book not found")

        def do_DELETE(self):
            book_id = self._book_id(urlparse(self.path).path)
            if book_id is None:
                return self._error(404, "not found")
            if store.delete(book_id):
                return self._send(204)
            self._error(404, "book not found")

    return BookHandler


def create_server(host="127.0.0.1", port=8000, db_path="books.db"):
    store = BookStore(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(store))
    server.store = store
    return server


def main():
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="SQLite database file")
    args = parser.parse_args()
    server = create_server(args.host, args.port, args.db)
    print(f"Serving on http://{args.host}:{args.port} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
