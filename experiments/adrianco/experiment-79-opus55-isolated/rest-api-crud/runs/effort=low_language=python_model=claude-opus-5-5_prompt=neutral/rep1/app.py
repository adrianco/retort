"""Book collection REST API built on the Python standard library and SQLite."""

import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

DEFAULT_DB = "books.db"
MAX_BODY_BYTES = 1_000_000
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ApiError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    with closing(connect(db_path)) as conn, conn:
        conn.execute(
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


def validate_book(data):
    """Return a cleaned book dict, or raise ApiError(400) listing every problem."""
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")

    errors = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = f"{field} is required and must be a non-empty string"

    year = data.get("year")
    # bool is a subclass of int, so reject it explicitly
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "year must be an integer"

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"

    if errors:
        raise ApiError(400, "Validation failed", errors)

    return {
        "title": data["title"].strip(),
        "author": data["author"].strip(),
        "year": year,
        "isbn": isbn,
    }


class BookStore:
    """SQLite-backed storage. Opens a connection per operation so it is thread-safe."""

    def __init__(self, db_path=DEFAULT_DB):
        self.db_path = db_path
        init_db(db_path)

    def create(self, book):
        with closing(connect(self.db_path)) as conn, conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            return {"id": cur.lastrowid, **book}

    def list(self, author=None):
        sql, params = "SELECT * FROM books", ()
        if author is not None:
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        with closing(connect(self.db_path)) as conn:
            return [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]

    def get(self, book_id):
        with closing(connect(self.db_path)) as conn:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return dict(row) if row else None

    def update(self, book_id, book):
        with closing(connect(self.db_path)) as conn, conn:
            cur = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            return {"id": book_id, **book} if cur.rowcount else None

    def delete(self, book_id):
        with closing(connect(self.db_path)) as conn, conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0


class BookHandler(BaseHTTPRequestHandler):
    store = None  # set by make_server

    def log_message(self, format, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(format, *args)

    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "Invalid Content-Length header")
        if length < 0:
            raise ApiError(400, "Invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            raise ApiError(413, "Request body too large")
        try:
            return json.loads(self.rfile.read(length))
        except (ValueError, RecursionError):
            raise ApiError(400, "Request body must be valid JSON")

    def _dispatch(self, method):
        try:
            self._route(method)
        except ApiError as e:
            payload = {"error": e.message}
            if e.details:
                payload["details"] = e.details
            self._send(e.status, payload)
        except Exception:
            self.close_connection = True
            self._send(500, {"error": "Internal server error"})

    def _route(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        store = self.server.store

        if path == "/health":
            if method != "GET":
                raise ApiError(405, "Method not allowed")
            return self._send(200, {"status": "ok"})

        if path == "/books":
            if method == "GET":
                author = parse_qs(url.query).get("author", [None])[0]
                return self._send(200, store.list(author))
            if method == "POST":
                book = store.create(validate_book(self._read_json()))
                return self._send(201, book)
            raise ApiError(405, "Method not allowed")

        match = BOOK_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = store.get(book_id)
            elif method == "PUT":
                book = store.update(book_id, validate_book(self._read_json()))
            elif method == "DELETE":
                if not store.delete(book_id):
                    raise ApiError(404, "Book not found")
                return self._send(204)
            else:
                raise ApiError(405, "Method not allowed")
            if book is None:
                raise ApiError(404, "Book not found")
            return self._send(200, book)

        raise ApiError(404, "Not found")

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        self._dispatch("PATCH")


def make_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB, quiet=False):
    server = ThreadingHTTPServer((host, port), BookHandler)
    server.store = BookStore(db_path)
    server.quiet = quiet
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("BOOKS_DB", DEFAULT_DB)
    server = make_server(host, port, db_path)
    print(f"Serving on http://{host}:{port} (db: {db_path})", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
