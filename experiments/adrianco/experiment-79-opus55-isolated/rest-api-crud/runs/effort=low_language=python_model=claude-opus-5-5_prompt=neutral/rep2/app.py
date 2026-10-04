"""Book collection REST API backed by SQLite, using only the standard library."""

import argparse
import json
import os
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BODY_BYTES = 1024 * 1024
BOOK_PATH = re.compile(r"^/books/(\d+)$")
FIELDS = ("title", "author", "year", "isbn")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class HTTPError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def validate_book(data):
    """Return a cleaned book dict, or raise ValidationError listing every problem."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    book = {}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str) or not value.strip():
            errors[field] = "must be a non-empty string"
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
    book["isbn"] = isbn.strip() if isinstance(isbn, str) else isbn

    if errors:
        raise ValidationError(errors)
    return book


class BookStore:
    """SQLite persistence. Opens a short-lived connection per operation so it is
    safe to use from the threaded server."""

    def __init__(self, db_path):
        self.db_path = db_path
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS books (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       title TEXT NOT NULL,
                       author TEXT NOT NULL,
                       year INTEGER,
                       isbn TEXT
                   )"""
            )

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, book):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                [book[f] for f in FIELDS],
            )
            return {"id": cur.lastrowid, **book}

    def list(self, author=None):
        query, params = "SELECT * FROM books", []
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params.append(author)
        with closing(self._connect()) as conn:
            return [dict(r) for r in conn.execute(query + " ORDER BY id", params)]

    def get(self, book_id):
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return dict(row) if row else None

    def update(self, book_id, book):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                [book[f] for f in FIELDS] + [book_id],
            )
            return {"id": book_id, **book} if cur.rowcount else None

    def delete(self, book_id):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0


class BookHandler(BaseHTTPRequestHandler):
    store = None  # set by make_server
    server_version = "BookAPI/1.0"

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

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise HTTPError(400, "invalid Content-Length")
        if length < 0:
            raise HTTPError(400, "invalid Content-Length")
        if length > MAX_BODY_BYTES:
            # The unread body would corrupt the next keep-alive request
            self.close_connection = True
            raise HTTPError(413, "request body too large")
        try:
            return json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, "request body must be valid JSON")

    def _dispatch(self):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        method = self.command

        if path == "/health":
            allowed = {"GET": self._health}
        elif path == "/books":
            allowed = {"GET": lambda: self._list_books(url.query), "POST": self._create_book}
        elif match := BOOK_PATH.match(path):
            book_id = int(match.group(1))
            allowed = {
                "GET": lambda: self._get_book(book_id),
                "PUT": lambda: self._update_book(book_id),
                "DELETE": lambda: self._delete_book(book_id),
            }
        else:
            raise HTTPError(404, "not found")

        if method not in allowed:
            self.close_connection = True  # any request body is left unread
            raise HTTPError(405, "method not allowed")
        allowed[method]()

    def _handle(self):
        try:
            self._dispatch()
        except ValidationError as exc:
            self._send_json(400, {"error": "validation failed", "details": exc.errors})
        except HTTPError as exc:
            self._send_json(exc.status, {"error": exc.message})
        except Exception:
            self.close_connection = True
            self._send_json(500, {"error": "internal server error"})

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle

    def _health(self):
        self._send_json(200, {"status": "ok"})

    def _list_books(self, query):
        author = parse_qs(query).get("author", [None])[0]
        self._send_json(200, self.store.list(author))

    def _create_book(self):
        book = self.store.create(validate_book(self._read_json()))
        self._send_json(201, book)

    def _get_book(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            raise HTTPError(404, "book not found")
        self._send_json(200, book)

    def _update_book(self, book_id):
        book = self.store.update(book_id, validate_book(self._read_json()))
        if book is None:
            raise HTTPError(404, "book not found")
        self._send_json(200, book)

    def _delete_book(self, book_id):
        if not self.store.delete(book_id):
            raise HTTPError(404, "book not found")
        self._send_json(204)


def make_server(host="127.0.0.1", port=8000, db_path="books.db", quiet=False):
    handler = type("BoundBookHandler", (BookHandler,), {"store": BookStore(db_path)})
    server = ThreadingHTTPServer((host, port), handler)
    server.quiet = quiet
    return server


def main():
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", "books.db"))
    args = parser.parse_args()

    server = make_server(args.host, args.port, args.db)
    print(f"Listening on http://{args.host}:{server.server_port} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
