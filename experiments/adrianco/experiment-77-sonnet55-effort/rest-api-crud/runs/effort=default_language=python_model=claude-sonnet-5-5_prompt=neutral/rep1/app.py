"""Book collection REST API using only the Python standard library."""
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_DB = os.environ.get("BOOKS_DB", "books.db")
FIELDS = ("title", "author", "year", "isbn")


class BookStore:
    def __init__(self, path=DEFAULT_DB):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.conn:
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT)"""
            )

    def _one(self, book_id):
        row = self.conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def create(self, data):
        with self.lock, self.conn:
            cur = self.conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                (data["title"], data["author"], data["year"], data["isbn"]),
            )
            return self._one(cur.lastrowid)

    def list(self, author=None):
        with self.lock:
            if author:
                rows = self.conn.execute(
                    "SELECT * FROM books WHERE author=? ORDER BY id", (author,))
            else:
                rows = self.conn.execute("SELECT * FROM books ORDER BY id")
            return [dict(r) for r in rows]

    def get(self, book_id):
        with self.lock:
            return self._one(book_id)

    def update(self, book_id, data):
        with self.lock, self.conn:
            cur = self.conn.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                (data["title"], data["author"], data["year"], data["isbn"], book_id),
            )
            return self._one(book_id) if cur.rowcount else None

    def delete(self, book_id):
        with self.lock, self.conn:
            return self.conn.execute("DELETE FROM books WHERE id=?", (book_id,)).rowcount > 0


def validate(data):
    """Return (clean_data, errors)."""
    if not isinstance(data, dict):
        return None, ["body must be a JSON object"]
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
    return clean, errors


BOOK_PATH = re.compile(r"^/books/(\d+)/?$")


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body=None):
            payload = b"" if body is None else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(length) or b"null"), None
            except (ValueError, UnicodeDecodeError):
                return None, "invalid JSON body"

        def _route(self):
            url = urlparse(self.path)
            path = url.path
            m = BOOK_PATH.match(path)
            method = self.command
            if path == "/health" and method == "GET":
                return self._send(200, {"status": "ok"})
            if path.rstrip("/") == "/books":
                if method == "GET":
                    author = parse_qs(url.query).get("author", [None])[0]
                    return self._send(200, store.list(author))
                if method == "POST":
                    data, err = self._read_json()
                    if err:
                        return self._send(400, {"error": err})
                    clean, errors = validate(data)
                    if errors:
                        return self._send(400, {"error": "validation failed", "details": errors})
                    return self._send(201, store.create(clean))
                return self._send(405, {"error": "method not allowed"})
            if m:
                book_id = int(m.group(1))
                if method == "GET":
                    book = store.get(book_id)
                elif method == "PUT":
                    data, err = self._read_json()
                    if err:
                        return self._send(400, {"error": err})
                    clean, errors = validate(data)
                    if errors:
                        return self._send(400, {"error": "validation failed", "details": errors})
                    book = store.update(book_id, clean)
                elif method == "DELETE":
                    if store.delete(book_id):
                        return self._send(204)
                    book = None
                else:
                    return self._send(405, {"error": "method not allowed"})
                if book is None:
                    return self._send(404, {"error": "book not found"})
                return self._send(200, book)
            self._send(404, {"error": "not found"})

        do_GET = do_POST = do_PUT = do_DELETE = _route


    return Handler


def create_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB):
    return ThreadingHTTPServer((host, port), make_handler(BookStore(db_path)))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    srv = create_server(port=port)
    print(f"Listening on http://127.0.0.1:{port}")
    srv.serve_forever()
