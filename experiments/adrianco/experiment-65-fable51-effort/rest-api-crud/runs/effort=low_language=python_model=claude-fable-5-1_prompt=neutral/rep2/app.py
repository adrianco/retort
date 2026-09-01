"""Book collection REST API built on the Python standard library.

Endpoints:
    GET    /health
    POST   /books
    GET    /books[?author=...]
    GET    /books/{id}
    PUT    /books/{id}
    DELETE /books/{id}
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")
BOOK_PATH_RE = re.compile(r"^/books/(\d+)/?$")


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """Thin SQLite-backed repository for books. Safe for use across threads."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
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
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {"id": row["id"], "title": row["title"], "author": row["author"],
                "year": row["year"], "isbn": row["isbn"]}

    def create(self, data: dict) -> dict:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn")),
            )
            self._conn.commit()
            book_id = cur.lastrowid
        return self.get(book_id)

    def list(self, author: str | None = None) -> list[dict]:
        with self._lock:
            if author is not None:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, book_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def update(self, book_id: int, data: dict) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data["title"], data["author"], data.get("year"), data.get("isbn"), book_id),
            )
            self._conn.commit()
            if cur.rowcount == 0:
                return None
        return self.get(book_id)

    def delete(self, book_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cur.rowcount > 0


def validate_book(payload) -> dict:
    """Validate and normalise an incoming book payload. Raises ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})
    errors: dict[str, str] = {}
    clean: dict = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            clean[field] = value.strip()

    year = payload.get("year")
    if year is None:
        clean["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    elif year < 0 or year > 9999:
        errors["year"] = "must be between 0 and 9999"
    else:
        clean["year"] = year

    isbn = payload.get("isbn")
    if isbn is None:
        clean["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        cleaned = isbn.replace("-", "").replace(" ", "")
        if not re.fullmatch(r"\d{9}[\dXx]|\d{13}", cleaned):
            errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
        else:
            clean["isbn"] = isbn.strip()

    if errors:
        raise ValidationError(errors)
    return clean


def make_handler(store: BookStore):
    class BookHandler(BaseHTTPRequestHandler):
        server_version = "BookAPI/1.0"

        # --- helpers -----------------------------------------------------
        def log_message(self, fmt, *args):  # quieter logs; still to stderr
            if os.environ.get("BOOKS_QUIET") != "1":
                sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _send_json(self, status: int, body=None) -> None:
            self.send_response(status)
            if body is None:
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            data = json.dumps(body).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _error(self, status: int, message: str, **extra) -> None:
            body = {"error": message}
            body.update(extra)
            self._send_json(status, body)

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if not raw:
                raise ValueError("empty body")
            return json.loads(raw)

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"

            if path == "/health" and method == "GET":
                return self._send_json(HTTPStatus.OK, {"status": "ok"})

            if path == "/books":
                if method == "GET":
                    return self._list_books(parsed.query)
                if method == "POST":
                    return self._create_book()
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")

            m = BOOK_PATH_RE.match(parsed.path)
            if m:
                book_id = int(m.group(1))
                if method == "GET":
                    return self._get_book(book_id)
                if method == "PUT":
                    return self._update_book(book_id)
                if method == "DELETE":
                    return self._delete_book(book_id)
                return self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")

            return self._error(HTTPStatus.NOT_FOUND, "not found")

        def _parse_body_or_400(self):
            try:
                payload = self._read_json()
            except (ValueError, json.JSONDecodeError):
                self._error(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")
                return None
            try:
                return validate_book(payload)
            except ValidationError as exc:
                self._error(HTTPStatus.BAD_REQUEST, "validation failed", details=exc.errors)
                return None

        # --- handlers ----------------------------------------------------
        def _list_books(self, query: str) -> None:
            params = parse_qs(query)
            author = params.get("author", [None])[0]
            self._send_json(HTTPStatus.OK, store.list(author))

        def _create_book(self) -> None:
            data = self._parse_body_or_400()
            if data is None:
                return
            book = store.create(data)
            self.send_response(HTTPStatus.CREATED)
            payload = json.dumps(book).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Location", f"/books/{book['id']}")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _get_book(self, book_id: int) -> None:
            book = store.get(book_id)
            if book is None:
                return self._error(HTTPStatus.NOT_FOUND, "book not found")
            self._send_json(HTTPStatus.OK, book)

        def _update_book(self, book_id: int) -> None:
            data = self._parse_body_or_400()
            if data is None:
                return
            book = store.update(book_id, data)
            if book is None:
                return self._error(HTTPStatus.NOT_FOUND, "book not found")
            self._send_json(HTTPStatus.OK, book)

        def _delete_book(self, book_id: int) -> None:
            if not store.delete(book_id):
                return self._error(HTTPStatus.NOT_FOUND, "book not found")
            self._send_json(HTTPStatus.NO_CONTENT)

        def do_GET(self):    self._dispatch("GET")
        def do_POST(self):   self._dispatch("POST")
        def do_PUT(self):    self._dispatch("PUT")
        def do_DELETE(self): self._dispatch("DELETE")

    return BookHandler


def create_server(host: str = "127.0.0.1", port: int = 8000,
                  db_path: str = DEFAULT_DB_PATH) -> tuple[ThreadingHTTPServer, BookStore]:
    store = BookStore(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(store))
    return server, store


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server, store = create_server(host, port)
    print(f"Book API listening on http://{host}:{port} (db: {store.db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
