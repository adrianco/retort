"""REST API for managing a book collection, backed by SQLite.

Built on the Python standard library only (http.server + sqlite3), so it runs
without installing any third-party packages.
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
from urllib.parse import parse_qs, urlparse

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")
MAX_BODY_BYTES = 1024 * 1024

BOOK_PATH = re.compile(r"/books/(\d+)")
ISBN_PATTERN = re.compile(r"^(\d{9}[\dXx]|\d{13})$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


class ValidationError(ValueError):
    """A request payload failed validation."""


def validate_book(payload, *, partial: bool = False) -> dict:
    """Validate a book payload and return the cleaned fields it contains.

    With ``partial=False`` (create) ``title`` and ``author`` are required.
    With ``partial=True`` (update) any subset of fields may be supplied, but
    any field that is supplied must be valid.
    """
    if not isinstance(payload, dict):
        raise ValidationError("request body must be a JSON object")

    errors = []
    cleaned = {}

    for field in ("title", "author"):
        if field not in payload:
            if not partial:
                errors.append(f"'{field}' is required")
            continue
        value = payload[field]
        if isinstance(value, str) and value.strip():
            cleaned[field] = value.strip()
        else:
            errors.append(f"'{field}' must be a non-empty string")

    if "year" in payload:
        year = payload["year"]
        max_year = datetime.date.today().year + 1
        if year is None:
            cleaned["year"] = None
        elif isinstance(year, int) and not isinstance(year, bool) and 1 <= year <= max_year:
            cleaned["year"] = year
        else:
            errors.append(f"'year' must be an integer between 1 and {max_year}")

    if "isbn" in payload:
        isbn = payload["isbn"]
        if isbn is None:
            cleaned["isbn"] = None
        elif isinstance(isbn, str) and ISBN_PATTERN.match(isbn.replace("-", "").replace(" ", "")):
            cleaned["isbn"] = isbn.replace("-", "").replace(" ", "")
        else:
            errors.append("'isbn' must be a valid 10- or 13-digit ISBN")

    if errors:
        raise ValidationError("; ".join(errors))
    return cleaned


class BookStore:
    """Thin SQLite-backed repository for books.

    A single connection is shared across request threads and guarded by a lock.
    """

    def __init__(self, path: str = DEFAULT_DB_PATH):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._conn:
            self._conn.execute(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def create(self, data: dict) -> dict:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn")),
            )
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_dict(row)

    def get(self, book_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def list(self, author: str | None = None) -> list[dict]:
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def update(self, book_id: int, changes: dict) -> dict | None:
        with self._lock, self._conn:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                return None
            merged = {**_row_to_dict(row), **changes}
            self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
            )
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_dict(row)

    def delete(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BooksAPI/1.0"

    @property
    def store(self) -> BookStore:
        return self.server.store  # type: ignore[attr-defined]

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        # Not supported; routed through dispatch so the client gets a JSON 405.
        self._dispatch("PATCH")

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path == "/health":
                return self._allow("GET", method, lambda: self._send_json(HTTPStatus.OK, {"status": "ok"}))

            if path == "/books":
                if method == "GET":
                    return self._list_books(parse_qs(parsed.query))
                if method == "POST":
                    return self._create_book()
                return self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed", allow="GET, POST")

            match = BOOK_PATH.fullmatch(path)
            if match:
                book_id = int(match.group(1))
                if method == "GET":
                    return self._get_book(book_id)
                if method == "PUT":
                    return self._update_book(book_id)
                if method == "DELETE":
                    return self._delete_book(book_id)
                return self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed", allow="GET, PUT, DELETE")

            return self._send_error(HTTPStatus.NOT_FOUND, "not found")
        except ValidationError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

    def _allow(self, expected: str, method: str, action) -> None:
        if method != expected:
            return self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed", allow=expected)
        return action()

    def _list_books(self, query: dict) -> None:
        author = query.get("author", [None])[0]
        books = self.store.list(author=author)
        self._send_json(HTTPStatus.OK, books)

    def _create_book(self) -> None:
        data = validate_book(self._read_json())
        book = self.store.create(data)
        self._send_json(HTTPStatus.CREATED, book, location=f"/books/{book['id']}")

    def _get_book(self, book_id: int) -> None:
        book = self.store.get(book_id)
        if book is None:
            return self._send_error(HTTPStatus.NOT_FOUND, "book not found")
        self._send_json(HTTPStatus.OK, book)

    def _update_book(self, book_id: int) -> None:
        changes = validate_book(self._read_json(), partial=True)
        book = self.store.update(book_id, changes)
        if book is None:
            return self._send_error(HTTPStatus.NOT_FOUND, "book not found")
        self._send_json(HTTPStatus.OK, book)

    def _delete_book(self, book_id: int) -> None:
        if not self.store.delete(book_id):
            return self._send_error(HTTPStatus.NOT_FOUND, "book not found")
        self._send_response(HTTPStatus.NO_CONTENT)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValidationError("invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise ValidationError(f"request body exceeds {MAX_BODY_BYTES} bytes")
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValidationError("request body must be valid JSON")

    def _send_json(self, status: HTTPStatus, body, location: str | None = None) -> None:
        payload = json.dumps(body).encode("utf-8")
        self._send_response(status, payload, location=location)

    def _send_error(self, status: HTTPStatus, message: str, allow: str | None = None) -> None:
        extra_headers = {"Allow": allow} if allow else None
        payload = json.dumps({"error": message}).encode("utf-8")
        self._send_response(status, payload, extra_headers=extra_headers)

    def _send_response(self, status: HTTPStatus, payload: bytes = b"", location: str | None = None,
                       extra_headers: dict | None = None) -> None:
        self.send_response(status)
        if payload:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
        else:
            self.send_header("Content-Length", "0")
        if location:
            self.send_header("Location", location)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if payload:
            self.wfile.write(payload)


def create_server(host: str = "127.0.0.1", port: int = 8000,
                  db_path: str = DEFAULT_DB_PATH) -> ThreadingHTTPServer:
    """Build a server bound to ``host:port`` backed by the SQLite file at ``db_path``."""
    server = ThreadingHTTPServer((host, port), BookRequestHandler)
    server.store = BookStore(db_path)  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite database file (env: BOOKS_DB)")
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port, args.db)
    print(f"Serving books API on http://{args.host}:{server.server_address[1]} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
