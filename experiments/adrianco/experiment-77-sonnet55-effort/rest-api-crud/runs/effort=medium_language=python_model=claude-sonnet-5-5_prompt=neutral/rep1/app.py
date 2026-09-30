"""Book collection REST API using only the Python standard library."""
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIELDS = ("title", "author", "year", "isbn")
BOOK_PATH = re.compile(r"^/books/(\d+)/?$")


class ValidationError(Exception):
    pass


class BookStore:
    def __init__(self, path=":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS books ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "title TEXT NOT NULL, author TEXT NOT NULL,"
                "year INTEGER, isbn TEXT)"
            )
            self.conn.commit()

    def _one(self, book_id):
        row = self.conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def create(self, data):
        with self.lock:
            cur = self.conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                (data["title"], data["author"], data["year"], data["isbn"]),
            )
            self.conn.commit()
            return self._one(cur.lastrowid)

    def list(self, author=None):
        with self.lock:
            if author:
                rows = self.conn.execute(
                    "SELECT * FROM books WHERE author=? ORDER BY id", (author,))
            else:
                rows = self.conn.execute("SELECT * FROM books ORDER BY id")
            return [dict(r) for r in rows.fetchall()]

    def get(self, book_id):
        with self.lock:
            return self._one(book_id)

    def update(self, book_id, data):
        with self.lock:
            if not self._one(book_id):
                return None
            self.conn.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                (data["title"], data["author"], data["year"], data["isbn"], book_id),
            )
            self.conn.commit()
            return self._one(book_id)

    def delete(self, book_id):
        with self.lock:
            cur = self.conn.execute("DELETE FROM books WHERE id=?", (book_id,))
            self.conn.commit()
            return cur.rowcount > 0


def validate(data):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError("body must be a JSON object")
    errors = []
    clean = {}
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{f} is required and must be a non-empty string")
        else:
            clean[f] = v.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    clean["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    clean["isbn"] = isbn
    if errors:
        raise ValidationError("; ".join(errors))
    return clean


class Handler(BaseHTTPRequestHandler):
    store: BookStore

    def log_message(self, *args):
        pass

    def _send(self, status, body=None):
        payload = b"" if body is None else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"")
        except (ValueError, UnicodeDecodeError):
            raise ValidationError("invalid JSON body")

    def _route(self, method):
        url = urlparse(self.path)
        path = url.path
        try:
            if path == "/health" and method == "GET":
                return self._send(200, {"status": "ok"})
            if path.rstrip("/") == "/books":
                if method == "POST":
                    return self._send(201, self.store.create(validate(self._body())))
                if method == "GET":
                    author = parse_qs(url.query).get("author", [None])[0]
                    return self._send(200, self.store.list(author))
                return self._send(405, {"error": "method not allowed"})
            m = BOOK_PATH.match(path)
            if m:
                bid = int(m.group(1))
                if method == "GET":
                    book = self.store.get(bid)
                elif method == "PUT":
                    book = self.store.update(bid, validate(self._body()))
                elif method == "DELETE":
                    if self.store.delete(bid):
                        return self._send(204)
                    book = None
                else:
                    return self._send(405, {"error": "method not allowed"})
                if book is None:
                    return self._send(404, {"error": "book not found"})
                return self._send(200, book)
            self._send(404, {"error": "not found"})
        except ValidationError as e:
            self._send(400, {"error": str(e)})
        except Exception:
            self._send(500, {"error": "internal server error"})

    def do_GET(self): self._route("GET")
    def do_POST(self): self._route("POST")
    def do_PUT(self): self._route("PUT")
    def do_DELETE(self): self._route("DELETE")


def make_server(db_path=":memory:", host="127.0.0.1", port=8000):
    handler = type("BoundHandler", (Handler,), {"store": BookStore(db_path)})
    return ThreadingHTTPServer((host, port), handler)


if __name__ == "__main__":
    server = make_server(
        os.environ.get("BOOKS_DB", "books.db"),
        os.environ.get("HOST", "127.0.0.1"),
        int(os.environ.get("PORT", "8000")),
    )
    print(f"Listening on http://{server.server_address[0]}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
