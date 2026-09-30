"""Book collection REST API using only the standard library (http.server + sqlite3)."""
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCHEMA = """CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
)"""
FIELDS = ("title", "author", "year", "isbn")


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute(SCHEMA)
            self.conn.commit()

    def _one(self, book_id):
        row = self.conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def create(self, d):
        with self.lock:
            cur = self.conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                tuple(d[f] for f in FIELDS))
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

    def update(self, book_id, d):
        with self.lock:
            cur = self.conn.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                tuple(d[f] for f in FIELDS) + (book_id,))
            self.conn.commit()
            return self._one(book_id) if cur.rowcount else None

    def delete(self, book_id):
        with self.lock:
            cur = self.conn.execute("DELETE FROM books WHERE id=?", (book_id,))
            self.conn.commit()
            return cur.rowcount > 0


def validate(data):
    """Return (clean_dict, error_message)."""
    if not isinstance(data, dict):
        return None, "body must be a JSON object"
    clean = {}
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            return None, f"{f} is required and must be a non-empty string"
        clean[f] = v.strip()
    year = data.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
        return None, "year must be an integer"
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "isbn must be a string"
    clean["year"], clean["isbn"] = year, isbn
    return clean, None


class Handler(BaseHTTPRequestHandler):
    store = None  # set by make_server

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
            return None, "invalid JSON"

    def _route(self):
        path, _, query = self.path.partition("?")
        path = path.rstrip("/") or "/"
        m = re.fullmatch(r"/books/(\d+)", path)
        return path, (int(m.group(1)) if m else None), query

    def do_GET(self):
        path, book_id, query = self._route()
        if path == "/health":
            return self._send(200, {"status": "ok"})
        if path == "/books":
            from urllib.parse import parse_qs
            author = parse_qs(query).get("author", [None])[0]
            return self._send(200, self.store.list(author))
        if book_id is not None:
            book = self.store.get(book_id)
            return self._send(200, book) if book else self._send(404, {"error": "book not found"})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        path, _, _ = self._route()
        if path != "/books":
            return self._send(404, {"error": "not found"})
        data, err = self._read_json()
        clean, err = (None, err) if err else validate(data)
        if err:
            return self._send(400, {"error": err})
        self._send(201, self.store.create(clean))

    def do_PUT(self):
        path, book_id, _ = self._route()
        if book_id is None:
            return self._send(404, {"error": "not found"})
        data, err = self._read_json()
        clean, err = (None, err) if err else validate(data)
        if err:
            return self._send(400, {"error": err})
        book = self.store.update(book_id, clean)
        self._send(200, book) if book else self._send(404, {"error": "book not found"})

    def do_DELETE(self):
        path, book_id, _ = self._route()
        if book_id is None:
            return self._send(404, {"error": "not found"})
        if self.store.delete(book_id):
            return self._send(204)
        self._send(404, {"error": "book not found"})


def make_server(db_path=":memory:", host="127.0.0.1", port=0):
    handler = type("BoundHandler", (Handler,), {"store": Store(db_path)})
    return ThreadingHTTPServer((host, port), handler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    srv = make_server(os.environ.get("DB_PATH", "books.db"), "0.0.0.0", port)
    print(f"Listening on port {port}")
    srv.serve_forever()
