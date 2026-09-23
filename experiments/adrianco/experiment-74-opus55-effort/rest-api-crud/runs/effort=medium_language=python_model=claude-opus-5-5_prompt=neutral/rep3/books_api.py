"""Book collection REST API built on the Python standard library.

Uses ``http.server`` for HTTP and ``sqlite3`` for storage, so it runs with no
third-party dependencies.

Endpoints:
    GET    /health
    POST   /books
    GET    /books[?author=...]
    GET    /books/{id}
    PUT    /books/{id}
    DELETE /books/{id}
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import threading
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

FIELDS = ("title", "author", "year", "isbn")
MAX_BODY_BYTES = 1 << 20  # 1 MiB
ISBN_RE = re.compile(r"^(?:\d{9}[\dX]|\d{13})$")


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


class ConflictError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
class BookStore:
    """Thread-safe SQLite-backed book repository."""

    def __init__(self, db_path: str = "books.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year   INTEGER,
                    isbn   TEXT UNIQUE
                )
                """
            )

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict | None:
        return dict(row) if row is not None else None

    def ping(self) -> bool:
        with self._lock:
            return self._conn.execute("SELECT 1").fetchone()[0] == 1

    def create(self, book: dict) -> dict:
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                        (book["title"], book["author"], book.get("year"), book.get("isbn")),
                    )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("a book with this isbn already exists") from exc
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._row(row)

    def list(self, author: str | None = None) -> list[dict]:
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id", (author,)
                ).fetchall()
        return [dict(r) for r in rows]

    def get(self, book_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row(row)

    def update(self, book_id: int, book: dict) -> dict | None:
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                        (book["title"], book["author"], book.get("year"), book.get("isbn"), book_id),
                    )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("a book with this isbn already exists") from exc
            if cur.rowcount == 0:
                return None
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row(row)

    def delete(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_book(data: object) -> dict:
    """Validate a request payload and return a normalised book dict."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    book: dict = {}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str) or not value.strip():
            errors[field] = "must be a non-empty string"
        elif len(value) > 500:
            errors[field] = "must be at most 500 characters"
        else:
            book[field] = value.strip()

    year = data.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "must be an integer"
        elif not (0 <= year <= date.today().year + 1):
            errors["year"] = f"must be between 0 and {date.today().year + 1}"
        else:
            book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            errors["isbn"] = "must be a string"
        else:
            normalised = isbn.replace("-", "").replace(" ", "").upper()
            if not ISBN_RE.match(normalised):
                errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
            else:
                book["isbn"] = normalised

    unknown = sorted(set(data) - set(FIELDS) - {"id"})
    if unknown:
        errors["unknown_fields"] = ", ".join(unknown)

    if errors:
        raise ValidationError(errors)
    return book


# --------------------------------------------------------------------------- #
# Routing (framework-independent, easy to unit test)
# --------------------------------------------------------------------------- #
BOOK_PATH_RE = re.compile(r"^/books/(\d+)$")


def _error(status: HTTPStatus, message: str, **extra) -> tuple[int, dict]:
    return status, {"error": message, **extra}


def handle_request(store: BookStore, method: str, raw_path: str, body: bytes | None = None) -> tuple[int, object]:
    """Dispatch a request and return ``(status_code, json_payload)``."""
    parts = urlsplit(raw_path)
    path = parts.path.rstrip("/") or "/"
    query = parse_qs(parts.query)

    def parse_body() -> object:
        if not body:
            raise ValidationError({"body": "request body is required"})
        try:
            return json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValidationError({"body": "must be valid JSON"})

    try:
        if path == "/health":
            if method != "GET":
                return _error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            try:
                store.ping()
                return HTTPStatus.OK, {"status": "ok", "database": "ok"}
            except sqlite3.Error:
                return HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "database": "unavailable"}

        if path == "/books":
            if method == "GET":
                author = query.get("author", [None])[0]
                return HTTPStatus.OK, store.list(author=author)
            if method == "POST":
                book = validate_book(parse_body())
                return HTTPStatus.CREATED, store.create(book)
            return _error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")

        match = BOOK_PATH_RE.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = store.get(book_id)
            elif method == "PUT":
                book = store.update(book_id, validate_book(parse_body()))
            elif method == "DELETE":
                if store.delete(book_id):
                    return HTTPStatus.NO_CONTENT, None
                book = None
            else:
                return _error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
            if book is None:
                return _error(HTTPStatus.NOT_FOUND, f"book {book_id} not found")
            return HTTPStatus.OK, book

        return _error(HTTPStatus.NOT_FOUND, "not found")
    except ValidationError as exc:
        return _error(HTTPStatus.BAD_REQUEST, "validation failed", details=exc.errors)
    except ConflictError as exc:
        return _error(HTTPStatus.CONFLICT, str(exc))


# --------------------------------------------------------------------------- #
# HTTP server
# --------------------------------------------------------------------------- #
def make_handler(store: BookStore) -> type[BaseHTTPRequestHandler]:
    class BookHandler(BaseHTTPRequestHandler):
        server_version = "BooksAPI/1.0"

        def _dispatch(self) -> None:
            body = None
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                self._send(*_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large"))
                return
            if length:
                body = self.rfile.read(length)
            self._send(*handle_request(store, self.command, self.path, body))

        def _send(self, status: int, payload: object) -> None:
            self.send_response(status)
            if status == HTTPStatus.NO_CONTENT:
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            data = json.dumps(payload).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _dispatch

        def log_message(self, fmt, *args):  # quieter default logging
            if not getattr(self.server, "quiet", False):
                super().log_message(fmt, *args)

    return BookHandler


def make_server(host: str = "127.0.0.1", port: int = 8000, db_path: str = "books.db", quiet: bool = False):
    store = BookStore(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(store))
    server.quiet = quiet
    server.store = store
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="SQLite database path")
    args = parser.parse_args(argv)

    server = make_server(args.host, args.port, args.db)
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
