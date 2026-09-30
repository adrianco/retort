"""Book collection REST API using only the Python standard library.

No third-party framework was specified and none is installed, so this uses
``http.server`` for HTTP and ``sqlite3`` for storage.
"""
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_DB = os.environ.get("BOOKS_DB", "books.db")
MAX_BODY = 1024 * 1024
BOOK_PATH = re.compile(r"^/books/([^/]+)/?$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """SQLite-backed book storage (thread-safe via a single locked connection)."""

    def __init__(self, path=DEFAULT_DB):
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

    def close(self):
        with self._lock:
            self._conn.close()

    def create(self, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data["year"], data["isbn"]),
            )
            return self._get(cur.lastrowid)

    def _get(self, book_id):
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def list(self, author=None):
        sql, args = "SELECT * FROM books", ()
        if author is not None:
            sql += " WHERE author = ? COLLATE NOCASE"
            args = (author,)
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql + " ORDER BY id", args)]

    def update(self, book_id, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data["title"], data["author"], data["year"], data["isbn"], book_id),
            )
            return self._get(book_id) if cur.rowcount else None

    def delete(self, book_id):
        with self._lock, self._conn:
            return self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,)).rowcount > 0


def validate_book(payload):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})
    errors = {}
    cleaned = {}
    for field in ("title", "author"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            cleaned[field] = value.strip()
    year = payload.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    cleaned["year"] = year
    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    cleaned["isbn"] = isbn.strip() if isinstance(isbn, str) else None
    if errors:
        raise ValidationError(errors)
    return cleaned


def parse_id(raw):
    """Book ids are positive integers; anything else can never match a book."""
    return int(raw) if raw.isascii() and raw.isdigit() else None


class Handler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"
    store: BookStore  # set on the server

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    # -- helpers ---------------------------------------------------------
    def _send(self, status, body=None):
        raw = b"" if body is None else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _error(self, status, message, **extra):
        self._send(status, {"error": message, **extra})

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            raise ValidationError({"body": "invalid or too large Content-Length"})
        try:
            return json.loads(self.rfile.read(length) or b"")
        except (ValueError, UnicodeDecodeError):
            raise ValidationError({"body": "must be valid JSON"})

    def _dispatch(self):
        url = urlparse(self.path)
        path = url.path
        store = self.server.store
        if path == "/health":
            if self.command not in ("GET", "HEAD"):
                return self._error(405, "method not allowed")
            return self._send(200, {"status": "ok"})
        if path.rstrip("/") == "/books":
            if self.command == "POST":
                return self._send(201, store.create(validate_book(self._read_json())))
            if self.command == "GET":
                author = parse_qs(url.query).get("author", [None])[0]
                return self._send(200, store.list(author))
            return self._error(405, "method not allowed")
        match = BOOK_PATH.match(path)
        if match:
            book_id = parse_id(match.group(1))
            if self.command in ("GET", "PUT", "DELETE"):
                if self.command == "GET":
                    book = store.get(book_id) if book_id else None
                elif self.command == "PUT":
                    data = validate_book(self._read_json())
                    book = store.update(book_id, data) if book_id else None
                else:
                    if book_id and store.delete(book_id):
                        return self._send(204)
                    book = None
                if book is None:
                    return self._error(404, "book not found")
                return self._send(200, book)
            return self._error(405, "method not allowed")
        return self._error(404, "not found")

    def _handle(self):
        try:
            self._dispatch()
        except ValidationError as exc:
            self._error(400, "validation failed", details=exc.errors)
        except Exception:  # pragma: no cover - defensive
            self._error(500, "internal server error")

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_PATCH = _handle


def make_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB, verbose=False):
    server = ThreadingHTTPServer((host, port), Handler)
    server.store = BookStore(db_path)
    server.verbose = verbose
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = make_server(host, port, verbose=True)
    print(f"Serving on http://{host}:{port} (db: {DEFAULT_DB})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
