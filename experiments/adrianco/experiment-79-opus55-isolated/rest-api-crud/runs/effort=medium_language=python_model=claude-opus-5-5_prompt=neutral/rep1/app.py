"""REST API for managing a book collection.

Built on the Python standard library only: ``http.server`` for HTTP and
``sqlite3`` for storage.

Run with ``python app.py`` (see README.md for options).
"""

import argparse
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BODY_BYTES = 1024 * 1024
MIN_YEAR, MAX_YEAR = 0, 9999
BOOK_FIELDS = ("title", "author", "year", "isbn")

# Ids are capped at 18 digits so they always fit in a SQLite INTEGER.
BOOK_PATH = re.compile(r"^/books/(\d{1,18})$")


class BookStore:
    """SQLite-backed storage for books.

    A single connection is shared between request threads and guarded by a
    lock, which also makes ``:memory:`` databases usable from the server.
    """

    def __init__(self, path=":memory:"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year   INTEGER,
                    isbn   TEXT
                )
                """
            )

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                [book[f] for f in BOOK_FIELDS],
            )
            return self._get(cur.lastrowid)

    def list(self, author=None):
        query = "SELECT * FROM books"
        params = []
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params.append(author)
        query += " ORDER BY id"
        with self._lock:
            return [dict(row) for row in self._conn.execute(query, params)]

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def update(self, book_id, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                [book[f] for f in BOOK_FIELDS] + [book_id],
            )
            if cur.rowcount == 0:
                return None
            return self._get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", [book_id])
            return cur.rowcount > 0

    def _get(self, book_id):
        row = self._conn.execute(
            "SELECT * FROM books WHERE id = ?", [book_id]
        ).fetchone()
        return dict(row) if row else None


def validate_book(data):
    """Validate a book payload.

    Returns ``(book, errors)`` where ``book`` is the normalised payload and
    ``errors`` is a list of human-readable problems (empty when valid).
    """
    if not isinstance(data, dict):
        return None, ["request body must be a JSON object"]

    errors = []
    book = {}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors.append(f"{field} is required")
        elif not isinstance(value, str):
            errors.append(f"{field} must be a string")
        elif not value.strip():
            errors.append(f"{field} must not be empty")
        else:
            book[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, but true/false is not a year.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    elif year is not None and not MIN_YEAR <= year <= MAX_YEAR:
        errors.append(f"year must be between {MIN_YEAR} and {MAX_YEAR}")
    else:
        book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    else:
        book["isbn"] = isbn.strip() if isbn else None

    return (None, errors) if errors else (book, [])


class HTTPError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


class BookHandler(BaseHTTPRequestHandler):
    server_version = "BooksAPI/1.0"

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def log_message(self, format, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(format, *args)

    @property
    def store(self):
        return self.server.store

    def _dispatch(self, method):
        try:
            self._route(method)
        except HTTPError as exc:
            body = {"error": exc.message}
            if exc.details:
                body["details"] = exc.details
            self._send_json(exc.status, body)
        except Exception:
            self.log_error("unhandled error for %s %s", method, self.path)
            self._send_json(500, {"error": "internal server error"})

    def _route(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"

        if path == "/health":
            self._allow(method, "GET")
            self.store.ping()
            self._send_json(200, {"status": "ok"})
            return

        if path == "/books":
            self._allow(method, "GET", "POST")
            if method == "GET":
                authors = parse_qs(url.query).get("author")
                author = authors[0] if authors else None
                self._send_json(200, self.store.list(author=author))
            else:
                book = self.store.create(self._read_book())
                self._send_json(
                    201, book, headers={"Location": f"/books/{book['id']}"}
                )
            return

        match = BOOK_PATH.match(path)
        if match:
            self._allow(method, "GET", "PUT", "DELETE")
            book_id = int(match.group(1))
            if method == "GET":
                book = self.store.get(book_id)
            elif method == "PUT":
                book = self.store.update(book_id, self._read_book())
            else:
                if not self.store.delete(book_id):
                    raise HTTPError(404, "book not found")
                self._send_empty(204)
                return
            if book is None:
                raise HTTPError(404, "book not found")
            self._send_json(200, book)
            return

        raise HTTPError(404, "not found")

    def _allow(self, method, *allowed):
        if method not in allowed:
            raise HTTPError(405, "method not allowed")

    def _read_book(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise HTTPError(400, "invalid Content-Length header") from None
        if length < 0:
            raise HTTPError(400, "invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise HTTPError(413, "request body too large")

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except (ValueError, RecursionError):
            raise HTTPError(400, "request body must be valid JSON") from None

        book, errors = validate_book(data)
        if errors:
            raise HTTPError(400, "validation failed", errors)
        return book

    def _send_json(self, status, payload, headers=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()


def make_server(host="127.0.0.1", port=8000, db_path="books.db", quiet=False):
    """Create (but do not start) the HTTP server. Use port 0 for any free port."""
    server = ThreadingHTTPServer((host, port), BookHandler)
    server.daemon_threads = True
    server.store = BookStore(db_path)
    server.quiet = quiet
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8000"))
    )
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", "books.db"))
    args = parser.parse_args(argv)

    server = make_server(args.host, args.port, args.db)
    host, port = server.server_address[:2]
    print(f"Serving on http://{host}:{port} (database: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
