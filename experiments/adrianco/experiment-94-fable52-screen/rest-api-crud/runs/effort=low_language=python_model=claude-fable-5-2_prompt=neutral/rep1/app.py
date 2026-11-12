"""Book collection REST API using only the Python standard library.

Run with:  python app.py [--host HOST] [--port PORT] [--db PATH]
"""

import argparse
import json
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BODY_BYTES = 1024 * 1024
FIELDS = ("title", "author", "year", "isbn")
BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(data):
    """Validate a book payload and return a normalised dict."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})
    errors = {}
    book = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            book[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, so exclude it explicitly
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    book["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    book["isbn"] = isbn

    if errors:
        raise ValidationError(errors)
    return book


class BookStore:
    """SQLite-backed storage. A single connection guarded by a lock."""

    def __init__(self, path=":memory:"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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

    def create(self, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                [book[f] for f in FIELDS],
            )
            return {"id": cur.lastrowid, **book}

    def list(self, author=None):
        sql, params = "SELECT * FROM books", []
        if author is not None:
            sql += " WHERE author = ? COLLATE NOCASE"
            params.append(author)
        with self._lock:
            rows = self._conn.execute(sql + " ORDER BY id", params).fetchall()
        return [dict(r) for r in rows]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return dict(row) if row else None

    def update(self, book_id, book):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                [book[f] for f in FIELDS] + [book_id],
            )
        return {"id": book_id, **book} if cur.rowcount else None

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0

    def close(self):
        with self._lock:
            self._conn.close()


class HTTPError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class BookHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"

    @property
    def store(self):
        return self.server.store

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        if getattr(self.server, "verbose", False):
            super().log_message(format, *args)

    # -- helpers ---------------------------------------------------------

    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            # Body length unknown, so the connection can't be reused safely.
            self.close_connection = True
            raise HTTPError(411, "Content-Length header is required")
        if length < 0 or length > MAX_BODY_BYTES:
            self.close_connection = True
            raise HTTPError(413, "request body too large")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, "request body must be valid JSON")

    def _dispatch(self):
        try:
            self._route()
        except ValidationError as exc:
            self._send(400, {"error": "validation failed", "details": exc.errors})
        except HTTPError as exc:
            self._send(exc.status, {"error": exc.message})
        except Exception:  # pragma: no cover - defensive
            self._send(500, {"error": "internal server error"})

    def _route(self):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        method = self.command

        if path == "/health":
            if method != "GET":
                raise HTTPError(405, "method not allowed")
            return self._send(200, {"status": "ok"})

        if path == "/books":
            if method == "GET":
                author = parse_qs(url.query).get("author", [None])[0]
                return self._send(200, self.store.list(author))
            if method == "POST":
                book = validate_book(self._read_json())
                return self._send(201, self.store.create(book))
            raise HTTPError(405, "method not allowed")

        match = BOOK_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = self.store.get(book_id)
            elif method == "PUT":
                book = self.store.update(book_id, validate_book(self._read_json()))
            elif method == "DELETE":
                if self.store.delete(book_id):
                    return self._send(204)
                book = None
            else:
                raise HTTPError(405, "method not allowed")
            if book is None:
                raise HTTPError(404, "book not found")
            return self._send(200, book)

        raise HTTPError(404, "not found")

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _dispatch


def create_server(host="127.0.0.1", port=8000, db_path="books.db", verbose=False):
    server = ThreadingHTTPServer((host, port), BookHandler)
    server.daemon_threads = True
    server.store = BookStore(db_path)
    server.verbose = verbose
    return server


def main():
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="SQLite database path")
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.db, verbose=True)
    print(f"Listening on http://{args.host}:{server.server_address[1]} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
