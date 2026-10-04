"""REST API for managing a book collection.

Built on the Python standard library only: http.server for HTTP and
sqlite3 for storage.
"""

import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BODY_BYTES = 1024 * 1024
BOOK_FIELDS = ("title", "author", "year", "isbn")

_BOOK_PATH = re.compile(r"^/books/([^/]+)$")


class ValidationError(Exception):
    """Raised when a request payload is not a valid book."""

    def __init__(self, details):
        super().__init__("validation failed")
        self.details = details


def validate_book(payload):
    """Return a cleaned book dict, or raise ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    book = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str):
            errors[field] = "must be a string"
        elif not value.strip():
            errors[field] = "must not be blank"
        else:
            book[field] = value.strip()

    year = payload.get("year")
    # bool is a subclass of int, but true/false is not a year.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    else:
        book["year"] = year

    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        book["isbn"] = isbn.strip() if isbn is not None else None

    if errors:
        raise ValidationError(errors)
    return book


class BookStore:
    """SQLite-backed storage for books."""

    def __init__(self, db_path="books.db"):
        # One shared connection guarded by a lock, so that ":memory:"
        # databases work with the threaded server.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )
                """
            )

    def close(self):
        with self._lock:
            self._conn.close()

    def create(self, book):
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                [book[field] for field in BOOK_FIELDS],
            )
            return self._get(cursor.lastrowid)

    def list(self, author=None):
        query = "SELECT * FROM books"
        params = []
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params.append(author)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def update(self, book_id, book):
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                [book[field] for field in BOOK_FIELDS] + [book_id],
            )
            if cursor.rowcount == 0:
                return None
            return self._get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    def _get(self, book_id):
        row = self._conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"

    @property
    def store(self):
        return self.server.store

    # -- HTTP verbs ---------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    # -- routing ------------------------------------------------------

    def _dispatch(self, method):
        try:
            self._route(method)
        except ValidationError as exc:
            self._send_error(400, "Validation failed", exc.details)
        except Exception:  # keep the server answering in JSON
            self.log_error("unhandled error on %s %s", method, self.path)
            self._send_error(500, "Internal server error")

    def _route(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"

        if path == "/health":
            if method != "GET":
                return self._method_not_allowed(["GET"])
            return self._send_json(200, {"status": "ok"})

        if path == "/books":
            if method == "GET":
                return self._list_books(url.query)
            if method == "POST":
                return self._create_book()
            return self._method_not_allowed(["GET", "POST"])

        match = _BOOK_PATH.match(path)
        if match:
            if method not in ("GET", "PUT", "DELETE"):
                return self._method_not_allowed(["GET", "PUT", "DELETE"])
            book_id = self._parse_id(match.group(1))
            if book_id is None:
                return self._send_error(404, "Book not found")
            if method == "GET":
                return self._get_book(book_id)
            if method == "PUT":
                return self._update_book(book_id)
            return self._delete_book(book_id)

        self._send_error(404, "Not found")

    # -- endpoints ----------------------------------------------------

    def _list_books(self, query):
        authors = parse_qs(query).get("author")
        author = authors[0] if authors else None
        self._send_json(200, self.store.list(author=author))

    def _create_book(self):
        payload = self._read_json()
        if payload is _INVALID:
            return
        book = self.store.create(validate_book(payload))
        self._send_json(201, book, headers={"Location": f"/books/{book['id']}"})

    def _get_book(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            return self._send_error(404, "Book not found")
        self._send_json(200, book)

    def _update_book(self, book_id):
        payload = self._read_json()
        if payload is _INVALID:
            return
        book = self.store.update(book_id, validate_book(payload))
        if book is None:
            return self._send_error(404, "Book not found")
        self._send_json(200, book)

    def _delete_book(self, book_id):
        if not self.store.delete(book_id):
            return self._send_error(404, "Book not found")
        self.send_response(204)
        self.end_headers()

    # -- helpers ------------------------------------------------------

    @staticmethod
    def _parse_id(raw):
        # SQLite rowids are 64-bit; anything else cannot be a stored book.
        if raw.isascii() and raw.isdigit() and len(raw) <= 18:
            return int(raw)
        return None

    def _read_json(self):
        """Parse the request body; on failure send a 4xx and return _INVALID."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0:
            self._send_error(400, "Invalid Content-Length header")
            return _INVALID
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            self._send_error(413, "Request body too large")
            return _INVALID
        try:
            return json.loads(self.rfile.read(length))
        except (ValueError, RecursionError):
            self._send_error(400, "Request body must be valid JSON")
            return _INVALID

    def _method_not_allowed(self, allowed):
        self._send_error(405, "Method not allowed", headers={"Allow": ", ".join(allowed)})

    def _send_error(self, status, message, details=None, headers=None):
        body = {"error": message}
        if details:
            body["details"] = details
        self._send_json(status, body, headers=headers)

    def _send_json(self, status, body, headers=None):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(format, *args)


# Sentinel: the body could not be read and an error response was already sent.
_INVALID = object()


def create_server(host="127.0.0.1", port=8000, db_path="books.db", quiet=False):
    """Build a server bound to host:port (port 0 picks a free port)."""
    server = ThreadingHTTPServer((host, port), BookRequestHandler)
    server.daemon_threads = True
    server.store = BookStore(db_path)
    server.quiet = quiet
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", "books.db")

    server = create_server(host, port, db_path)
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
