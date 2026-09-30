"""Book collection REST API using only the Python standard library."""
import json
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

DEFAULT_DB = os.environ.get("BOOKS_DB", "books.db")
MAX_BODY = 1024 * 1024
FIELDS = ("title", "author", "year", "isbn")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(data):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})
    errors = {}
    out = {}
    for key in ("title", "author"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            errors[key] = "is required and must be a non-empty string"
        else:
            out[key] = value.strip()
    year = data.get("year")
    if year is None:
        out["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    elif not -10000 <= year <= 9999:
        errors["year"] = "is out of range"
    else:
        out["year"] = year
    isbn = data.get("isbn")
    if isbn is None:
        out["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        out["isbn"] = isbn.strip() or None
    if errors:
        raise ValidationError(errors)
    return out


class BookStore:
    def __init__(self, path=DEFAULT_DB):
        self.path = path
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS books ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "title TEXT NOT NULL, author TEXT NOT NULL,"
                "year INTEGER, isbn TEXT)"
            )
        conn.close()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _run(self, sql, params=()):
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute(sql, params)
                return cur.lastrowid, cur.rowcount, [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def create(self, book):
        new_id, _, _ = self._run(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            tuple(book[f] for f in FIELDS),
        )
        return self.get(new_id)

    def list(self, author=None):
        if author:
            sql, params = "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        else:
            sql, params = "SELECT * FROM books ORDER BY id", ()
        return self._run(sql, params)[2]

    def get(self, book_id):
        rows = self._run("SELECT * FROM books WHERE id = ?", (book_id,))[2]
        return rows[0] if rows else None

    def update(self, book_id, book):
        _, count, _ = self._run(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            tuple(book[f] for f in FIELDS) + (book_id,),
        )
        return self.get(book_id) if count else None

    def delete(self, book_id):
        return self._run("DELETE FROM books WHERE id = ?", (book_id,))[1] > 0


BOOK_PATH = re.compile(r"^/books/(\d+)$")


class Handler(BaseHTTPRequestHandler):
    store = None  # set by make_server
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if os.environ.get("BOOKS_QUIET") != "1":
            super().log_message(fmt, *args)

    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValidationError({"body": "invalid Content-Length"})
        if length > MAX_BODY:
            raise ValidationError({"body": "request body too large"})
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValidationError({"body": "must be valid JSON"})

    def _dispatch(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        try:
            if path == "/health" and method == "GET":
                return self._send(200, {"status": "ok"})
            if path == "/books":
                if method == "GET":
                    author = parse_qs(url.query).get("author", [None])[0]
                    return self._send(200, self.store.list(author))
                if method == "POST":
                    book = self.store.create(validate_book(self._read_json()))
                    return self._send(201, book)
            m = BOOK_PATH.match(path)
            if m:
                book_id = int(m.group(1))
                if method == "GET":
                    book = self.store.get(book_id)
                elif method == "PUT":
                    book = self.store.update(book_id, validate_book(self._read_json()))
                elif method == "DELETE":
                    return self._send(204) if self.store.delete(book_id) else self._send(
                        404, {"error": "book not found"})
                else:
                    return self._send(405, {"error": "method not allowed"})
                if book is None:
                    return self._send(404, {"error": "book not found"})
                return self._send(200, book)
            if path in ("/health", "/books"):
                return self._send(405, {"error": "method not allowed"})
            return self._send(404, {"error": "not found"})
        except ValidationError as exc:
            self._send(400, {"error": "validation failed", "details": exc.errors})
        except Exception:  # pragma: no cover - defensive
            self._send(500, {"error": "internal server error"})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")


def make_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB):
    handler = type("BoundHandler", (Handler,), {"store": BookStore(db_path)})
    return ThreadingHTTPServer((host, port), handler)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = make_server(host, port)
    print(f"Serving on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
