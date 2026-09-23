"""Book collection REST API using only the Python standard library (http.server + sqlite3)."""

import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIELDS = ("title", "author", "year", "isbn")
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class BookStore:
    """SQLite-backed storage for books. Thread-safe via a single lock."""

    def __init__(self, db_path=":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )"""
            )

    @staticmethod
    def _row(row):
        return dict(row) if row else None

    def create(self, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                tuple(data.get(f) for f in FIELDS),
            )
            book_id = cur.lastrowid
        return self.get(book_id)

    def list(self, author=None):
        with self._lock:
            if author:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row(row)

    def update(self, book_id, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (*(data.get(f) for f in FIELDS), book_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()


def validate_book(payload):
    """Validate and normalise a book payload. Returns a clean dict or raises ValidationError."""
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
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "must be an integer"
        elif not -5000 <= year <= 9999:
            errors["year"] = "must be between -5000 and 9999"
    clean["year"] = year

    isbn = payload.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            errors["isbn"] = "must be a string"
        else:
            digits = isbn.replace("-", "").replace(" ", "")
            if not re.fullmatch(r"\d{9}[\dXx]|\d{13}", digits):
                errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
    clean["isbn"] = isbn

    unknown = set(payload) - set(FIELDS) - {"id"}
    if unknown:
        errors["unknown_fields"] = sorted(unknown)
    if errors:
        raise ValidationError(errors)
    return clean


class BookAPI:
    """Framework-independent request routing: handle(...) -> (status, body)."""

    def __init__(self, store):
        self.store = store

    def handle(self, method, raw_path, body=b""):
        url = urlparse(raw_path)
        path = url.path.rstrip("/") or "/"
        query = parse_qs(url.query)

        if path == "/health":
            if method != "GET":
                return 405, {"error": "method not allowed"}
            try:
                self.store.ping()
            except sqlite3.Error:
                return 503, {"status": "error", "database": "unavailable"}
            return 200, {"status": "ok", "database": "ok"}

        if path == "/books":
            if method == "GET":
                author = query.get("author", [None])[0]
                return 200, self.store.list(author)
            if method == "POST":
                data, err = self._parse(body)
                if err:
                    return err
                return 201, self.store.create(data)
            return 405, {"error": "method not allowed"}

        match = BOOK_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = self.store.get(book_id)
                return (200, book) if book else self._not_found(book_id)
            if method == "PUT":
                data, err = self._parse(body)
                if err:
                    return err
                book = self.store.update(book_id, data)
                return (200, book) if book else self._not_found(book_id)
            if method == "DELETE":
                if self.store.delete(book_id):
                    return 204, None
                return self._not_found(book_id)
            return 405, {"error": "method not allowed"}

        return 404, {"error": "not found"}

    @staticmethod
    def _not_found(book_id):
        return 404, {"error": f"book {book_id} not found"}

    @staticmethod
    def _parse(body):
        try:
            payload = json.loads(body or b"")
        except (ValueError, UnicodeDecodeError):
            return None, (400, {"error": "invalid JSON body"})
        try:
            return validate_book(payload), None
        except ValidationError as exc:
            return None, (422, {"error": "validation failed", "details": exc.errors})


def make_handler(api):
    class Handler(BaseHTTPRequestHandler):
        def _dispatch(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            try:
                status, payload = api.handle(self.command, self.path, body)
            except Exception:  # pragma: no cover - defensive
                status, payload = 500, {"error": "internal server error"}
            self.send_response(status)
            if payload is None:
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            data = json.dumps(payload).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _dispatch

        def log_message(self, fmt, *args):
            if os.environ.get("BOOKS_API_QUIET") != "1":
                super().log_message(fmt, *args)

    return Handler


def create_server(host="127.0.0.1", port=8000, db_path="books.db"):
    api = BookAPI(BookStore(db_path))
    return ThreadingHTTPServer((host, port), make_handler(api))


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", "books.db")
    server = create_server(host, port, db_path)
    print(f"Serving books API on http://{host}:{port} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
