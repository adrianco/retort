"""Book collection REST API.

Built on the Python standard library only: ``http.server`` for HTTP and
``sqlite3`` for storage. Run with ``python app.py``.
"""

import json
import os
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

DEFAULT_DB_PATH = "books.db"
MAX_BODY_BYTES = 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

BOOK_PATH = re.compile(r"^/books/([^/]+)$")


class ApiError(Exception):
    """An error that maps directly onto a JSON HTTP response."""

    def __init__(self, status, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or {}

    def body(self):
        body = {"error": self.message}
        if self.details:
            body["details"] = self.details
        return body


def validate_book(data):
    """Return a cleaned book dict from a decoded JSON body, or raise ApiError(400)."""
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")

    errors = {}
    book = {}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors[field] = f"{field} is required"
        elif not isinstance(value, str):
            errors[field] = f"{field} must be a string"
        elif not value.strip():
            errors[field] = f"{field} must not be empty"
        else:
            book[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, but true/false is not a year.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "year must be an integer"
    book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"
    else:
        book["isbn"] = isbn.strip() or None if isbn else None

    if errors:
        raise ApiError(400, "Validation failed", errors)
    return book


class BookStore:
    """SQLite-backed storage. Opens a connection per operation, so it is thread-safe."""

    def __init__(self, path=DEFAULT_DB_PATH):
        self.path = path
        with closing(self._connect()) as conn, conn:
            conn.execute(SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, book):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            return {"id": cur.lastrowid, **book}

    def list(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        with closing(self._connect()) as conn:
            return [dict(row) for row in conn.execute(query + " ORDER BY id", params)]

    def get(self, book_id):
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            return dict(row) if row else None

    def update(self, book_id, book):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            return {"id": book_id, **book} if cur.rowcount else None

    def delete(self, book_id):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0


class BookHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"

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

    def _dispatch(self, method):
        try:
            status, body, headers = self._route(method)
        except ApiError as err:
            status, body, headers = err.status, err.body(), err.headers
        except Exception as err:  # never leak a traceback to the client
            self.log_error("Unhandled error: %r", err)
            status, body, headers = 500, {"error": "Internal server error"}, {}
        self._send(status, body, headers)

    def _route(self, method):
        """Return (status, body, extra_headers) for the current request."""
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        store = self.server.store

        if path == "/health":
            self._require(method, "GET")
            return 200, {"status": "ok"}, {}

        if path == "/books":
            self._require(method, "GET", "POST")
            if method == "GET":
                authors = parse_qs(url.query).get("author")
                return 200, store.list(authors[0] if authors else None), {}
            book = store.create(validate_book(self._read_json()))
            return 201, book, {"Location": f"/books/{book['id']}"}

        match = BOOK_PATH.match(path)
        if match:
            self._require(method, "GET", "PUT", "DELETE")
            book_id = self._parse_id(match.group(1))
            if method == "GET":
                book = store.get(book_id)
            elif method == "PUT":
                book = store.update(book_id, validate_book(self._read_json()))
            else:
                if store.delete(book_id):
                    return 204, None, {}
                book = None
            if book is None:
                raise ApiError(404, "Book not found")
            return 200, book, {}

        raise ApiError(404, "Not found")

    @staticmethod
    def _require(method, *allowed):
        if method not in allowed:
            raise ApiError(405, "Method not allowed", headers={"Allow": ", ".join(allowed)})

    @staticmethod
    def _parse_id(raw):
        # A non-numeric or out-of-range ID cannot name an existing book.
        if not raw.isascii() or not raw.isdigit() or len(raw) > 18:
            raise ApiError(404, "Book not found")
        return int(raw)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "Invalid Content-Length header") from None
        if length < 0:
            raise ApiError(400, "Invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise ApiError(413, "Request body too large")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "Request body must be valid JSON") from None

    def _send(self, status, body, headers):
        payload = b"" if body is None else json.dumps(body).encode("utf-8")
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        if body is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def create_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB_PATH, quiet=False):
    """Build a ready-to-serve HTTP server; pass port=0 for an ephemeral port."""
    server = ThreadingHTTPServer((host, port), BookHandler)
    server.store = BookStore(db_path)
    server.quiet = quiet
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)
    server = create_server(host, port, db_path)
    print(f"Book API listening on http://{host}:{server.server_address[1]} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
