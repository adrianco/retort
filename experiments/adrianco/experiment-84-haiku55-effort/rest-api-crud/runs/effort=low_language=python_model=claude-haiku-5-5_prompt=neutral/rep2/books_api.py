"""REST API for managing a book collection, backed by SQLite.

Uses only the Python standard library (http.server + sqlite3), so it runs
without installing anything. Run with:  python books_api.py
"""

import json
import os
import re
import sqlite3
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""

BOOK_ID_RE = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    """Raised when a request payload fails validation."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """Thin SQLite-backed repository. Serialises access with a lock so one
    connection can safely be shared across request threads."""

    def __init__(self, path=DEFAULT_DB_PATH):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    def close(self):
        self._conn.close()

    @staticmethod
    def _row_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def create(self, data):
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data["year"], data["isbn"]),
            )
            self._conn.commit()
            new_id = cur.lastrowid
        return self.get(new_id)

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, author=None):
        query = "SELECT * FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update(self, book_id, data):
        with self._lock:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data["title"], data["author"], data["year"], data["isbn"], book_id),
            )
            self._conn.commit()
            if cur.rowcount == 0:
                return None
        return self.get(book_id)

    def delete(self, book_id):
        with self._lock:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cur.rowcount > 0


def validate_book(payload):
    """Validate and normalise a book payload. Title and author are required;
    year and isbn are optional. Returns a clean dict or raises ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    clean = {}

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
        clean["isbn"] = isbn.strip() or None

    if errors:
        raise ValidationError(errors)
    return clean


def make_handler(store):
    """Build a request handler class bound to the given BookStore."""

    class BooksHandler(BaseHTTPRequestHandler):
        server_version = "BooksAPI/1.0"

        # ---- helpers -------------------------------------------------
        def _send_json(self, status, body=None, headers=None):
            data = b"" if body is None else json.dumps(body).encode("utf-8")
            self.send_response(status)
            if body is not None:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            if data:
                self.wfile.write(data)

        def _send_error_json(self, status, message, details=None):
            body = {"error": message}
            if details is not None:
                body["details"] = details
            self._send_json(status, body)

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                return json.loads(raw.decode("utf-8") or "null")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValidationError({"body": "invalid JSON"})

        def _route(self):
            """Return (path, book_id) where book_id is None for /books."""
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            match = BOOK_ID_RE.match(path)
            if match:
                return "/books/{id}", int(match.group(1)), parsed
            return path, None, parsed

        def _dispatch(self, method):
            path, book_id, parsed = self._route()

            if path == "/health":
                if method != "GET":
                    return self._method_not_allowed("GET")
                return self._send_json(HTTPStatus.OK, {"status": "ok"})

            if path == "/books":
                if method == "GET":
                    return self._list_books(parsed)
                if method == "POST":
                    return self._create_book()
                return self._method_not_allowed("GET, POST")

            if path == "/books/{id}":
                if method == "GET":
                    return self._get_book(book_id)
                if method == "PUT":
                    return self._update_book(book_id)
                if method == "DELETE":
                    return self._delete_book(book_id)
                return self._method_not_allowed("GET, PUT, DELETE")

            return self._send_error_json(HTTPStatus.NOT_FOUND, "not found")

        def _method_not_allowed(self, allowed):
            self._send_json(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {"error": "method not allowed"},
                headers={"Allow": allowed},
            )

        # ---- handlers ------------------------------------------------
        def _list_books(self, parsed):
            params = parse_qs(parsed.query)
            author = params.get("author", [None])[0]
            self._send_json(HTTPStatus.OK, store.list(author=author))

        def _create_book(self):
            try:
                data = validate_book(self._read_json())
            except ValidationError as exc:
                return self._send_error_json(
                    HTTPStatus.BAD_REQUEST, "validation failed", exc.errors
                )
            book = store.create(data)
            self._send_json(
                HTTPStatus.CREATED,
                book,
                headers={"Location": f"/books/{book['id']}"},
            )

        def _get_book(self, book_id):
            book = store.get(book_id)
            if book is None:
                return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
            self._send_json(HTTPStatus.OK, book)

        def _update_book(self, book_id):
            try:
                data = validate_book(self._read_json())
            except ValidationError as exc:
                return self._send_error_json(
                    HTTPStatus.BAD_REQUEST, "validation failed", exc.errors
                )
            book = store.update(book_id, data)
            if book is None:
                return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
            self._send_json(HTTPStatus.OK, book)

        def _delete_book(self, book_id):
            if not store.delete(book_id):
                return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
            self._send_json(HTTPStatus.NO_CONTENT)

        # ---- HTTP verbs ----------------------------------------------
        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def do_PUT(self):
            self._dispatch("PUT")

        def do_DELETE(self):
            self._dispatch("DELETE")

        def do_PATCH(self):
            # Not supported, but routed through dispatch so clients get the
            # same JSON 404/405 responses as every other verb.
            self._dispatch("PATCH")

        def log_message(self, format, *args):  # keep test output quiet
            if os.environ.get("BOOKS_API_LOG"):
                super().log_message(format, *args)

    return BooksHandler


def create_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB_PATH):
    store = BookStore(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(store))
    server.store = store
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = create_server(host, port)
    print(f"Books API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
