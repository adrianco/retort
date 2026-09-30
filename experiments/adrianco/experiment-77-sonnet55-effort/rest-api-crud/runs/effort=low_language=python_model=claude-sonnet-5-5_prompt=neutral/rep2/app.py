"""Book collection REST API using only the Python standard library + SQLite."""
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIELDS = ("title", "author", "year", "isbn")


class BookStore:
    def __init__(self, path=":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"
            )
            self.conn.commit()

    def _one(self, book_id):
        row = self.conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def create(self, d):
        with self.lock:
            cur = self.conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                (d["title"], d["author"], d["year"], d["isbn"]),
            )
            self.conn.commit()
            return self._one(cur.lastrowid)

    def list(self, author=None):
        with self.lock:
            if author:
                rows = self.conn.execute("SELECT * FROM books WHERE author=? ORDER BY id", (author,))
            else:
                rows = self.conn.execute("SELECT * FROM books ORDER BY id")
            return [dict(r) for r in rows.fetchall()]

    def get(self, book_id):
        with self.lock:
            return self._one(book_id)

    def update(self, book_id, d):
        with self.lock:
            if not self._one(book_id):
                return None
            self.conn.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                (d["title"], d["author"], d["year"], d["isbn"], book_id),
            )
            self.conn.commit()
            return self._one(book_id)

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
            return None, f"'{f}' is required and must be a non-empty string"
        clean[f] = v.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return None, "'year' must be an integer"
    clean["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "'isbn' must be a string"
    clean["isbn"] = isbn
    return clean, None


BOOK_RE = re.compile(r"^/books/(\d+)$")


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
            self.wfile.write(payload)

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"null"), None
            except (ValueError, UnicodeDecodeError):
                return None, "invalid JSON"

        def _route(self, method):
            url = urlparse(self.path)
            path = url.path.rstrip("/") or "/"
            m = BOOK_RE.match(path)
            if path == "/health" and method == "GET":
                return self._send(200, {"status": "ok"})
            if path == "/books":
                if method == "GET":
                    author = parse_qs(url.query).get("author", [None])[0]
                    return self._send(200, store.list(author))
                if method == "POST":
                    data, err = self._body()
                    clean, err = (None, err) if err else validate(data)
                    if err:
                        return self._send(400, {"error": err})
                    return self._send(201, store.create(clean))
            elif m:
                bid = int(m.group(1))
                if method == "GET":
                    book = store.get(bid)
                elif method == "PUT":
                    data, err = self._body()
                    clean, err = (None, err) if err else validate(data)
                    if err:
                        return self._send(400, {"error": err})
                    book = store.update(bid, clean)
                elif method == "DELETE":
                    if store.delete(bid):
                        return self._send(204)
                    book = None
                else:
                    return self._send(405, {"error": "method not allowed"})
                if book is None:
                    return self._send(404, {"error": "book not found"})
                return self._send(200, book)
            else:
                return self._send(404, {"error": "not found"})
            return self._send(405, {"error": "method not allowed"})

        def do_GET(self): self._route("GET")
        def do_POST(self): self._route("POST")
        def do_PUT(self): self._route("PUT")
        def do_DELETE(self): self._route("DELETE")

    return Handler


def create_server(host="127.0.0.1", port=8000, db_path=":memory:"):
    return ThreadingHTTPServer((host, port), make_handler(BookStore(db_path)))


if __name__ == "__main__":
    srv = create_server(
        os.environ.get("HOST", "127.0.0.1"),
        int(os.environ.get("PORT", "8000")),
        os.environ.get("DB_PATH", "books.db"),
    )
    print(f"Listening on {srv.server_address}")
    srv.serve_forever()
