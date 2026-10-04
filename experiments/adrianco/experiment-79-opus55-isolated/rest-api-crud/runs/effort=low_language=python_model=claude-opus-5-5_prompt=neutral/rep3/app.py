"""Book collection REST API built on the Python standard library and SQLite."""

import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_BODY_BYTES = 1_000_000
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class DuplicateISBNError(Exception):
    pass


def validate_book(data):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str) or not value.strip():
            errors[field] = "must be a non-empty string"
        else:
            cleaned[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, so exclude it explicitly
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    cleaned["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str) or not isbn.strip():
            errors["isbn"] = "must be a non-empty string"
        else:
            isbn = isbn.strip()
    cleaned["isbn"] = isbn

    if errors:
        raise ValidationError(errors)
    return cleaned


class BookStore:
    """SQLite-backed storage for books."""

    def __init__(self, path="books.db"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT UNIQUE
                )
                """
            )

    def close(self):
        with self._lock:
            self._conn.close()

    def create(self, book):
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                        (book["title"], book["author"], book["year"], book["isbn"]),
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBNError() from exc
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
            return [dict(row) for row in rows]

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def update(self, book_id, book):
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                        (book["title"], book["author"], book["year"], book["isbn"], book_id),
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBNError() from exc
            if cur.rowcount == 0:
                return None
            return self._get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def _get(self, book_id):
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None


class BookHandler(BaseHTTPRequestHandler):
    store = None  # set by make_server

    def log_message(self, format, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(format, *args)

    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message, **extra):
        self._send(status, {"error": message, **extra})

    def _read_json(self):
        """Return the parsed body, or None after sending an error response."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = -1
        if length < 0:
            self._error(400, "invalid Content-Length")
            return None
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            self._error(413, "request body too large")
            return None
        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self._error(400, "request body must be valid JSON")
            return None
        try:
            return validate_book(data)
        except ValidationError as exc:
            self._error(422, "validation failed", details=exc.errors)
            return None

    def _route(self, method):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        match = BOOK_PATH.match(path)

        if path == "/health":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._send(200, {"status": "ok"})

        if path == "/books":
            if method == "GET":
                authors = parse_qs(url.query).get("author")
                return self._send(200, self.store.list(authors[0] if authors else None))
            if method == "POST":
                book = self._read_json()
                if book is None:
                    return None
                try:
                    return self._send(201, self.store.create(book))
                except DuplicateISBNError:
                    return self._error(409, "a book with this isbn already exists")
            return self._method_not_allowed("GET, POST")

        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = self.store.get(book_id)
            elif method == "PUT":
                data = self._read_json()
                if data is None:
                    return None
                try:
                    book = self.store.update(book_id, data)
                except DuplicateISBNError:
                    return self._error(409, "a book with this isbn already exists")
            elif method == "DELETE":
                if self.store.delete(book_id):
                    return self._send(204)
                book = None
            else:
                return self._method_not_allowed("GET, PUT, DELETE")
            if book is None:
                return self._error(404, "book not found")
            return self._send(200, book)

        return self._error(404, "not found")

    def _method_not_allowed(self, allowed):
        body = json.dumps({"error": "method not allowed"}).encode("utf-8")
        self.send_response(405)
        self.send_header("Allow", allowed)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")

    def do_PATCH(self):
        self._route("PATCH")


def make_server(host="127.0.0.1", port=8000, db_path="books.db", quiet=False):
    store = BookStore(db_path)
    handler = type("BoundBookHandler", (BookHandler,), {"store": store})
    server = ThreadingHTTPServer((host, port), handler)
    server.quiet = quiet
    server.store = store
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", "books.db")
    server = make_server(host, port, db_path)
    print(f"Serving on http://{host}:{port} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
