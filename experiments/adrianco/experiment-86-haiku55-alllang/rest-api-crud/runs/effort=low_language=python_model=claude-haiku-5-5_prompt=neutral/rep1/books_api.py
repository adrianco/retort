"""REST API for managing a book collection.

Built on the standard library only: ``http.server`` for HTTP and ``sqlite3``
for storage, so it runs without installing anything.

Run with:  python books_api.py [--host 127.0.0.1] [--port 8000] [--db books.db]
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
from typing import Any
from urllib.parse import parse_qs, urlsplit

MAX_BODY_BYTES = 1024 * 1024
MIN_YEAR = 0
MAX_YEAR = date.today().year + 1
ISBN_PATTERN = re.compile(r"^[0-9X-]{10,17}$")  # ISBN-10/13, optionally hyphenated


class ValidationError(Exception):
    """Raised when a payload fails validation; carries per-field messages."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """SQLite-backed storage for books. Thread-safe via a single lock."""

    def __init__(self, path: str = ":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
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
                    isbn   TEXT
                )
                """
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn")),
            )
            new_id = cur.lastrowid
        return self.get(new_id)  # type: ignore[return-value]

    def list(self, author: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM books"
        params: tuple[Any, ...] = ()
        if author is not None:
            sql += " WHERE LOWER(author) = LOWER(?)"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def update(self, book_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        """Apply the fields present in ``data`` to the book. Returns None if missing."""
        allowed = ("title", "author", "year", "isbn")
        fields = {k: data[k] for k in allowed if k in data}
        with self._lock, self._conn:
            if not self._exists(book_id):
                return None
            if fields:
                assignments = ", ".join(f"{k} = ?" for k in fields)
                self._conn.execute(
                    f"UPDATE books SET {assignments} WHERE id = ?",
                    (*fields.values(), book_id),
                )
        return self.get(book_id)

    def delete(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def _exists(self, book_id: int) -> bool:
        return self._conn.execute("SELECT 1 FROM books WHERE id = ?", (book_id,)).fetchone() is not None


def _check_text(value: Any, field: str, errors: dict[str, str]) -> None:
    if value is None:
        errors[field] = f"{field} must not be null"
    elif not isinstance(value, str):
        errors[field] = f"{field} must be a string"
    elif not value.strip():
        errors[field] = f"{field} must not be empty"


def validate_book(data: Any, partial: bool = False) -> dict[str, Any]:
    """Validate a book payload and return the cleaned fields.

    With ``partial=True`` (used for PUT), absent fields are not required.
    Raises ValidationError with per-field messages on failure.
    """
    if not isinstance(data, dict):
        raise ValidationError({"body": "request body must be a JSON object"})

    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}
    required = not partial

    for field in ("title", "author"):
        if field in data:
            _check_text(data[field], field, errors)
            if field not in errors:
                cleaned[field] = data[field].strip()
        elif required:
            errors[field] = f"{field} is required"

    if "isbn" in data:
        isbn = data["isbn"]
        if isbn is None:
            cleaned["isbn"] = None
        elif not isinstance(isbn, str) or not ISBN_PATTERN.match(isbn):
            errors["isbn"] = "isbn must be a valid ISBN-10 or ISBN-13 string"
        else:
            cleaned["isbn"] = isbn

    if "year" in data:
        year = data["year"]
        if year is None:
            cleaned["year"] = None
        elif isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "year must be an integer"
        elif not MIN_YEAR <= year <= MAX_YEAR:
            errors["year"] = f"year must be between {MIN_YEAR} and {MAX_YEAR}"
        else:
            cleaned["year"] = year

    if errors:
        raise ValidationError(errors)
    return cleaned


class BooksRequestHandler(BaseHTTPRequestHandler):
    server: "BooksHTTPServer"  # narrow the type for editors

    server_version = "BooksAPI/1.0"

    # --- routing -----------------------------------------------------------

    def do_GET(self) -> None:
        path, query = self._split_path()
        if path == "/health":
            return self._send_json(HTTPStatus.OK, {"status": "ok"})
        if path == "/books":
            author = query.get("author", [None])[0]
            return self._send_json(HTTPStatus.OK, self.server.store.list(author))
        if (book_id := self._book_id(path)) is not None:
            book = self.server.store.get(book_id)
            if book is None:
                return self._not_found()
            return self._send_json(HTTPStatus.OK, book)
        return self._not_found()

    def do_POST(self) -> None:
        path, _ = self._split_path()
        if path != "/books":
            return self._not_found()
        try:
            data = validate_book(self._read_json())
        except ValidationError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, "validation failed", exc.errors)
        except ValueError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
        book = self.server.store.create(data)
        self._send_json(HTTPStatus.CREATED, book, location=f"/books/{book['id']}")

    def do_PUT(self) -> None:
        path, _ = self._split_path()
        book_id = self._book_id(path)
        if book_id is None:
            return self._not_found()
        try:
            data = validate_book(self._read_json(), partial=True)
        except ValidationError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, "validation failed", exc.errors)
        except ValueError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
        book = self.server.store.update(book_id, data)
        if book is None:
            return self._not_found()
        self._send_json(HTTPStatus.OK, book)

    def do_DELETE(self) -> None:
        path, _ = self._split_path()
        book_id = self._book_id(path)
        if book_id is None:
            return self._not_found()
        if not self.server.store.delete(book_id):
            return self._not_found()
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _method_not_allowed(self) -> None:
        self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, f"method {self.command} not allowed")

    do_HEAD = do_PATCH = do_OPTIONS = _method_not_allowed

    # --- helpers -----------------------------------------------------------

    def _split_path(self) -> tuple[str, dict[str, list[str]]]:
        parts = urlsplit(self.path)
        return parts.path.rstrip("/") or "/", parse_qs(parts.query)

    @staticmethod
    def _book_id(path: str) -> int | None:
        match = re.fullmatch(r"/books/(\d+)", path)
        return int(match.group(1)) if match else None

    def _read_json(self) -> Any:
        length = self.headers.get("Content-Length")
        if length is None:
            raise ValueError("Content-Length header is required")
        try:
            size = int(length)
        except ValueError:
            raise ValueError("invalid Content-Length header") from None
        if size > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(size)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("request body is not valid JSON") from None

    def _send_json(self, status: HTTPStatus, payload: Any, location: str | None = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if location:
            self.send_header("Location", location)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str, details: dict[str, str] | None = None) -> None:
        payload: dict[str, Any] = {"error": message}
        if details:
            payload["details"] = details
        self._send_json(status, payload)

    def _not_found(self) -> None:
        self._send_error(HTTPStatus.NOT_FOUND, "not found")

    def log_message(self, format: str, *args: Any) -> None:  # keep test output quiet
        pass


class BooksHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: BookStore):
        super().__init__(address, BooksRequestHandler)
        self.store = store


def create_server(host: str = "127.0.0.1", port: int = 8000, db_path: str = ":memory:") -> BooksHTTPServer:
    return BooksHTTPServer((host, port), BookStore(db_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Books REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="SQLite database file")
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
