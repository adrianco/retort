"""Book collection REST API built on the Python standard library and SQLite."""

import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_BODY_BYTES = 1024 * 1024
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(data):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str) or not value.strip():
            errors[field] = "must be a non-empty string"
        else:
            cleaned[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, so reject it explicitly
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    cleaned["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    cleaned["isbn"] = isbn

    if errors:
        raise ValidationError(errors)
    return cleaned


class BookStore:
    """SQLite-backed storage for books."""

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
            return {"id": cur.lastrowid, **book}

    def list(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        with self._lock:
            rows = self._conn.execute(query + " ORDER BY id", params).fetchall()
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
    server_version = "BookAPI/1.0"
    # HTTP/1.0 closes the connection after each response, so a rejected
    # request with an unread body can never desynchronise a kept-alive socket.
    protocol_version = "HTTP/1.0"

    @property
    def store(self):
        return self.server.store

    def log_message(self, format, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(format, *args)

    def _send_json(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, status, message, details=None):
        payload = {"error": message}
        if details:
            payload["details"] = details
        self._send_json(status, payload)

    def _read_json(self):
        """Parse the request body; on failure send an error and return None."""
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._error(411, "Content-Length header is required")
            return None
        if length < 0:
            self._error(400, "invalid Content-Length")
            return None
        if length > MAX_BODY_BYTES:
            self._error(413, "request body too large")
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._error(400, "request body must be valid JSON")
            return None

    def _route(self):
        """Return (path, query, book_id); book_id is None for non-item paths."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        match = BOOK_PATH.match(path)
        return path, parse_qs(parsed.query), int(match.group(1)) if match else None

    def _not_found_or_not_allowed(self, path, book_id):
        if path in ("/books", "/health") or book_id is not None:
            self._error(405, "method not allowed")
        else:
            self._error(404, "not found")

    def do_GET(self):
        path, query, book_id = self._route()
        if path == "/health":
            self._send_json(200, {"status": "ok"})
        elif path == "/books":
            author = query.get("author", [None])[0]
            self._send_json(200, self.store.list(author=author))
        elif book_id is not None:
            book = self.store.get(book_id)
            if book is None:
                self._error(404, "book not found")
            else:
                self._send_json(200, book)
        else:
            self._error(404, "not found")

    def do_POST(self):
        path, _, book_id = self._route()
        if path != "/books":
            self._not_found_or_not_allowed(path, book_id)
            return
        data = self._read_json()
        if data is None:
            return
        try:
            book = validate_book(data)
        except ValidationError as exc:
            self._error(400, "validation failed", exc.errors)
            return
        created = self.store.create(book)
        self._send_json(201, created)

    def do_PUT(self):
        path, _, book_id = self._route()
        if book_id is None:
            self._not_found_or_not_allowed(path, book_id)
            return
        data = self._read_json()
        if data is None:
            return
        try:
            book = validate_book(data)
        except ValidationError as exc:
            self._error(400, "validation failed", exc.errors)
            return
        updated = self.store.update(book_id, book)
        if updated is None:
            self._error(404, "book not found")
        else:
            self._send_json(200, updated)

    def do_DELETE(self):
        path, _, book_id = self._route()
        if book_id is None:
            self._not_found_or_not_allowed(path, book_id)
        elif self.store.delete(book_id):
            self._send_json(204)
        else:
            self._error(404, "book not found")


def create_server(host="127.0.0.1", port=8000, db_path="books.db", quiet=False):
    server = ThreadingHTTPServer((host, port), BookHandler)
    server.store = BookStore(db_path)
    server.quiet = quiet
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("DATABASE_PATH", "books.db")
    server = create_server(host, port, db_path)
    print(f"Book API listening on http://{host}:{port} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
