"""Book collection REST API built on the Python standard library and SQLite."""

import argparse
import json
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_BODY_BYTES = 1024 * 1024
BOOK_PATH = re.compile(r"^/books/(\d+)$")
_INVALID = object()  # returned by _read_json once an error response was sent


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_book(data):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError(["request body must be a JSON object"])

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
        raise ValidationError(errors)
    return book


class BookStore:
    """SQLite-backed storage. A single connection is shared under a lock."""

    def __init__(self, db_path="books.db"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            book_id = cur.lastrowid
        return {"id": book_id, **book}

    def list(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        return dict(row) if row else None

    def update(self, book_id, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            if cur.rowcount == 0:
                return None
        return {"id": book_id, **book}

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0


class BookHandler(BaseHTTPRequestHandler):
    store = None  # set by create_server
    server_version = "BookAPI/1.0"

    def log_message(self, format, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(format, *args)

    def _send_json(self, status, payload=None, headers=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message, details=None, headers=None):
        payload = {"error": message}
        if details:
            payload["details"] = details
        self._send_json(status, payload, headers)

    def _read_json(self):
        """Return the parsed body, or _INVALID after sending an error response."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = -1
        if length < 0:
            self.close_connection = True
            self._error(400, "invalid Content-Length header")
            return _INVALID
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            self._error(413, "request body too large")
            return _INVALID
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(400, "request body must be valid JSON")
            return _INVALID

    def _read_book(self):
        """Return a validated book, or None after sending an error response."""
        data = self._read_json()
        if data is _INVALID:
            return None
        try:
            return validate_book(data)
        except ValidationError as exc:
            self._error(400, "validation failed", exc.errors)
            return None

    def _route(self, method):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"

        if path == "/health":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._send_json(200, {"status": "ok"})

        if path == "/books":
            if method == "GET":
                authors = parse_qs(url.query).get("author")
                return self._send_json(200, self.store.list(authors[0] if authors else None))
            if method == "POST":
                book = self._read_book()
                if book is None:
                    return None
                created = self.store.create(book)
                return self._send_json(201, created, {"Location": f"/books/{created['id']}"})
            return self._method_not_allowed("GET, POST")

        match = BOOK_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = self.store.get(book_id)
                if book is None:
                    return self._error(404, "book not found")
                return self._send_json(200, book)
            if method == "PUT":
                book = self._read_book()
                if book is None:
                    return None
                updated = self.store.update(book_id, book)
                if updated is None:
                    return self._error(404, "book not found")
                return self._send_json(200, updated)
            if method == "DELETE":
                if not self.store.delete(book_id):
                    return self._error(404, "book not found")
                return self._send_json(204)
            return self._method_not_allowed("GET, PUT, DELETE")

        return self._error(404, "not found")

    def _method_not_allowed(self, allowed):
        self._error(405, "method not allowed", headers={"Allow": allowed})

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


def create_server(host="127.0.0.1", port=8000, db_path="books.db", quiet=False):
    """Build a ready-to-serve HTTP server bound to its own BookStore."""
    store = BookStore(db_path)
    handler = type("BoundBookHandler", (BookHandler,), {"store": store})
    server = ThreadingHTTPServer((host, port), handler)
    server.store = store
    server.quiet = quiet
    return server


def main():
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="path to the SQLite database file")
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.db)
    print(f"Serving on http://{args.host}:{server.server_address[1]} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
