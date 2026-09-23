"""Book collection REST API.

A small JSON-over-HTTP service backed by SQLite, built only on the Python
standard library (http.server + sqlite3) so it runs with no extra packages.

Endpoints:
    GET    /health          liveness + database check
    POST   /books           create a book
    GET    /books           list books (optional ?author= filter)
    GET    /books/{id}      fetch one book
    PUT    /books/{id}      replace a book
    DELETE /books/{id}      delete a book
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BODY_BYTES = 1024 * 1024
MAX_TITLE_LEN = 500
MAX_AUTHOR_LEN = 300
ISBN_RE = re.compile(r"^(?:\d{9}[\dX]|\d{13})$")


class ValidationError(Exception):
    """Raised when a request payload fails validation."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


class DuplicateISBNError(Exception):
    """Raised when an ISBN is already used by another book."""


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def _normalize_isbn(raw: str) -> str:
    return raw.replace("-", "").replace(" ", "").upper()


def validate_book(payload: object) -> dict:
    """Validate a create/update payload and return the cleaned book fields.

    title and author are required non-empty strings; year and isbn are
    optional. Unknown fields are ignored.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    cleaned: dict = {}

    for field, max_len in (("title", MAX_TITLE_LEN), ("author", MAX_AUTHOR_LEN)):
        value = payload.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str):
            errors[field] = "must be a string"
        elif not value.strip():
            errors[field] = "must not be empty"
        elif len(value.strip()) > max_len:
            errors[field] = f"must be at most {max_len} characters"
        else:
            cleaned[field] = value.strip()

    year = payload.get("year")
    if year is None:
        cleaned["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    elif not -5000 <= year <= datetime.date.today().year + 1:
        errors["year"] = "is out of range"
    else:
        cleaned["year"] = year

    isbn = payload.get("isbn")
    if isbn is None or (isinstance(isbn, str) and not isbn.strip()):
        cleaned["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        normalized = _normalize_isbn(isbn)
        if not ISBN_RE.match(normalized):
            errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
        else:
            cleaned["isbn"] = normalized

    if errors:
        raise ValidationError(errors)
    return cleaned


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

class BookRepository:
    """SQLite-backed storage for books. Safe to share across threads."""

    def __init__(self, db_path: str = ":memory:"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_books_author "
                "ON books (author COLLATE NOCASE)"
            )

    @staticmethod
    def _to_dict(row: sqlite3.Row | None) -> dict | None:
        return dict(row) if row is not None else None

    def ping(self) -> bool:
        try:
            with self._lock:
                self._conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def create(self, book: dict) -> dict:
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "INSERT INTO books (title, author, year, isbn) "
                        "VALUES (:title, :author, :year, :isbn)",
                        book,
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBNError() from exc
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        return self._to_dict(row)

    def list(self, author: str | None = None) -> list[dict]:
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author.strip(),),
                ).fetchall()
        return [dict(r) for r in rows]

    def get(self, book_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return self._to_dict(row)

    def update(self, book_id: int, book: dict) -> dict | None:
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "UPDATE books SET title = :title, author = :author, "
                        "year = :year, isbn = :isbn WHERE id = :id",
                        {**book, "id": book_id},
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBNError() from exc
            if cur.rowcount == 0:
                return None
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return self._to_dict(row)

    def delete(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# --------------------------------------------------------------------------
# HTTP layer
# --------------------------------------------------------------------------

BOOK_PATH_RE = re.compile(r"^/books/(\d+)$")


class BookAPIHandler(BaseHTTPRequestHandler):
    """Routes requests to the repository. `repo` is set by make_server()."""

    repo: BookRepository
    server_version = "BookAPI/1.0"
    protocol_version = "HTTP/1.1"
    quiet = False

    # ---- response helpers -------------------------------------------------

    def _send_json(self, status: HTTPStatus, body: object = None,
                   headers: dict[str, str] | None = None) -> None:
        data = b"" if body is None else json.dumps(body).encode("utf-8")
        self.send_response(status)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _send_error(self, status: HTTPStatus, message: str,
                    details: dict | None = None,
                    headers: dict[str, str] | None = None) -> None:
        body: dict = {"error": message}
        if details:
            body["details"] = details
        self._send_json(status, body, headers)

    def _read_json(self) -> object:
        """Read and decode the request body; returns _BAD_BODY on error."""
        length_header = self.headers.get("Content-Length")
        try:
            length = int(length_header) if length_header else 0
        except ValueError:
            length = -1
        if length < 0:
            self._send_error(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
            return _BAD_BODY
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body too large")
            return _BAD_BODY
        raw = self.rfile.read(length) if length else b""
        if not raw.strip():
            self._send_error(HTTPStatus.BAD_REQUEST, "Request body is required")
            return _BAD_BODY
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON")
            return _BAD_BODY

    # ---- routing ----------------------------------------------------------

    def _route(self, method: str) -> None:
        parts = urlsplit(self.path)
        path = parts.path.rstrip("/") or "/"
        query = parse_qs(parts.query)

        try:
            if path == "/health":
                if method == "GET":
                    return self._health()
                return self._method_not_allowed("GET")
            if path == "/books":
                if method == "GET":
                    return self._list_books(query)
                if method == "POST":
                    return self._create_book()
                return self._method_not_allowed("GET, POST")
            match = BOOK_PATH_RE.match(path)
            if match:
                book_id = int(match.group(1))
                if method == "GET":
                    return self._get_book(book_id)
                if method == "PUT":
                    return self._update_book(book_id)
                if method == "DELETE":
                    return self._delete_book(book_id)
                return self._method_not_allowed("GET, PUT, DELETE")
            self._send_error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception:  # noqa: BLE001 - last-resort guard for a 500
            self.log_error("Unhandled error processing %s %s", method, self.path)
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def _method_not_allowed(self, allowed: str) -> None:
        self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed",
                         headers={"Allow": allowed})

    def do_GET(self) -> None:  # noqa: N802
        self._route("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._route("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._route("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._route("DELETE")

    def do_PATCH(self) -> None:  # noqa: N802
        self._route("PATCH")

    # ---- endpoint handlers -------------------------------------------------

    def _health(self) -> None:
        if self.repo.ping():
            self._send_json(HTTPStatus.OK, {"status": "ok", "database": "ok"})
        else:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE,
                            {"status": "error", "database": "unavailable"})

    def _list_books(self, query: dict[str, list[str]]) -> None:
        author = query.get("author", [None])[0]
        self._send_json(HTTPStatus.OK, self.repo.list(author=author))

    def _get_book(self, book_id: int) -> None:
        book = self.repo.get(book_id)
        if book is None:
            return self._send_error(HTTPStatus.NOT_FOUND, "Book not found")
        self._send_json(HTTPStatus.OK, book)

    def _create_book(self) -> None:
        payload = self._read_json()
        if payload is _BAD_BODY:
            return
        try:
            book = self.repo.create(validate_book(payload))
        except ValidationError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, "Validation failed", exc.errors)
        except DuplicateISBNError:
            return self._send_error(HTTPStatus.CONFLICT,
                                    "A book with this ISBN already exists")
        self._send_json(HTTPStatus.CREATED, book,
                        headers={"Location": f"/books/{book['id']}"})

    def _update_book(self, book_id: int) -> None:
        payload = self._read_json()
        if payload is _BAD_BODY:
            return
        try:
            book = self.repo.update(book_id, validate_book(payload))
        except ValidationError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, "Validation failed", exc.errors)
        except DuplicateISBNError:
            return self._send_error(HTTPStatus.CONFLICT,
                                    "A book with this ISBN already exists")
        if book is None:
            return self._send_error(HTTPStatus.NOT_FOUND, "Book not found")
        self._send_json(HTTPStatus.OK, book)

    def _delete_book(self, book_id: int) -> None:
        if not self.repo.delete(book_id):
            return self._send_error(HTTPStatus.NOT_FOUND, "Book not found")
        self._send_json(HTTPStatus.NO_CONTENT)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        if not self.quiet:
            super().log_message(format, *args)


_BAD_BODY = object()


def make_server(repo: BookRepository, host: str = "127.0.0.1", port: int = 8000,
                quiet: bool = False) -> ThreadingHTTPServer:
    """Build an HTTP server bound to host:port that serves `repo`."""
    handler = type("BoundBookAPIHandler", (BookAPIHandler,),
                   {"repo": repo, "quiet": quiet})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", "books.db"),
                        help="SQLite database file (use :memory: for ephemeral)")
    args = parser.parse_args(argv)

    repo = BookRepository(args.db)
    server = make_server(repo, args.host, args.port)
    print(f"Serving book API on http://{args.host}:{server.server_port} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        repo.close()


if __name__ == "__main__":
    main()
