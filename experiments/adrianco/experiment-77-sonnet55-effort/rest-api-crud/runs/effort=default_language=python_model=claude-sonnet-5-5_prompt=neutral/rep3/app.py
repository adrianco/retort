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


class Store:
    def __init__(self, path=":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS books ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "title TEXT NOT NULL, author TEXT NOT NULL,"
                "year INTEGER, isbn TEXT)"
            )

    def create(self, b):
        with self.lock, self.conn:
            cur = self.conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                (b["title"], b["author"], b["year"], b["isbn"]),
            )
            return self._get(cur.lastrowid)

    def _get(self, book_id):
        row = self.conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def get(self, book_id):
        with self.lock:
            return self._get(book_id)

    def list(self, author=None):
        with self.lock:
            if author:
                rows = self.conn.execute(
                    "SELECT * FROM books WHERE author=? ORDER BY id", (author,))
            else:
                rows = self.conn.execute("SELECT * FROM books ORDER BY id")
            return [dict(r) for r in rows.fetchall()]

    def update(self, book_id, b):
        with self.lock, self.conn:
            cur = self.conn.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                (b["title"], b["author"], b["year"], b["isbn"], book_id),
            )
            return self._get(book_id) if cur.rowcount else None

    def delete(self, book_id):
        with self.lock, self.conn:
            return self.conn.execute("DELETE FROM books WHERE id=?", (book_id,)).rowcount > 0


def validate(data):
    """Return (clean_book, errors)."""
    if not isinstance(data, dict):
        return None, ["body must be a JSON object"]
    errors = []
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{f} is required and must be a non-empty string")
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    if errors:
        return None, errors
    return {
        "title": data["title"].strip(),
        "author": data["author"].strip(),
        "year": year,
        "isbn": isbn,
    }, []


class Handler(BaseHTTPRequestHandler):
    store: Store = None

    def log_message(self, *args):
        pass

    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"null"), None
        except (ValueError, UnicodeDecodeError):
            return None, "invalid JSON body"

    def _route(self, method):
        url = urlparse(self.path)
        path = url.path
        if path == "/health" and method == "GET":
            return self._send(200, {"status": "ok"})
        if path.rstrip("/") == "/books":
            if method == "GET":
                author = parse_qs(url.query).get("author", [None])[0]
                return self._send(200, self.store.list(author))
            if method == "POST":
                data, err = self._read_json()
                if err:
                    return self._send(400, {"error": err})
                book, errors = validate(data)
                if errors:
                    return self._send(422, {"error": "validation failed", "details": errors})
                return self._send(201, self.store.create(book))
            return self._send(405, {"error": "method not allowed"})
        m = BOOK_PATH.match(path)
        if m:
            book_id = int(m.group(1))
            if method == "GET":
                book = self.store.get(book_id)
            elif method == "PUT":
                data, err = self._read_json()
                if err:
                    return self._send(400, {"error": err})
                clean, errors = validate(data)
                if errors:
                    return self._send(422, {"error": "validation failed", "details": errors})
                book = self.store.update(book_id, clean)
            elif method == "DELETE":
                if self.store.delete(book_id):
                    return self._send(204)
                book = None
            else:
                return self._send(405, {"error": "method not allowed"})
            if book is None:
                return self._send(404, {"error": "book not found"})
            return self._send(200, book)
        self._send(404, {"error": "not found"})

    def do_GET(self): self._route("GET")
    def do_POST(self): self._route("POST")
    def do_PUT(self): self._route("PUT")
    def do_DELETE(self): self._route("DELETE")


def make_server(host="127.0.0.1", port=8000, db_path=":memory:"):
    handler = type("BoundHandler", (Handler,), {"store": Store(db_path)})
    return ThreadingHTTPServer((host, port), handler)


if __name__ == "__main__":
    server = make_server(
        os.environ.get("HOST", "127.0.0.1"),
        int(os.environ.get("PORT", "8000")),
        os.environ.get("DB_PATH", "books.db"),
    )
    print(f"Listening on http://{server.server_address[0]}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
