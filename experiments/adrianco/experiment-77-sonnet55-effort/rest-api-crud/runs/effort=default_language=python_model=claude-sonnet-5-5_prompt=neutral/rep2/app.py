"""Book collection REST API using only the Python standard library + SQLite."""
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIELDS = ("title", "author", "year", "isbn")


class ValidationError(Exception):
    pass


class BookStore:
    def __init__(self, path=":memory:"):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS books ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
            "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
        )
        self._db.commit()

    def create(self, data):
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                tuple(data[f] for f in FIELDS),
            )
            self._db.commit()
            return self.get(cur.lastrowid)

    def get(self, book_id):
        row = self._db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def list(self, author=None):
        if author:
            rows = self._db.execute(
                "SELECT * FROM books WHERE author=? ORDER BY id", (author,)
            )
        else:
            rows = self._db.execute("SELECT * FROM books ORDER BY id")
        return [dict(r) for r in rows.fetchall()]

    def update(self, book_id, data):
        with self._lock:
            cur = self._db.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                (*(data[f] for f in FIELDS), book_id),
            )
            self._db.commit()
            return self.get(book_id) if cur.rowcount else None

    def delete(self, book_id):
        with self._lock:
            cur = self._db.execute("DELETE FROM books WHERE id=?", (book_id,))
            self._db.commit()
            return cur.rowcount > 0


def validate(payload):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError("body must be a JSON object")
    out = {}
    for f in ("title", "author"):
        v = payload.get(f)
        if not isinstance(v, str) or not v.strip():
            raise ValidationError(f"{f} is required and must be a non-empty string")
        out[f] = v.strip()
    year = payload.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
        raise ValidationError("year must be an integer")
    out["year"] = year
    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        raise ValidationError("isbn must be a string")
    out["isbn"] = isbn
    return out


BOOK_PATH = re.compile(r"^/books/(\d+)/?$")


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body=None):
            raw = b"" if body is None else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _body(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
                return validate(json.loads(self.rfile.read(length) or b"null"))
            except (ValueError, UnicodeDecodeError):
                raise ValidationError("invalid JSON body")

        def _route(self, method):
            url = urlparse(self.path)
            path = url.path
            try:
                if path == "/health" and method == "GET":
                    return self._send(200, {"status": "ok"})
                if path.rstrip("/") == "/books":
                    if method == "GET":
                        author = parse_qs(url.query).get("author", [None])[0]
                        return self._send(200, store.list(author))
                    if method == "POST":
                        return self._send(201, store.create(self._body()))
                    return self._send(405, {"error": "method not allowed"})
                m = BOOK_PATH.match(path)
                if m:
                    bid = int(m.group(1))
                    if method == "GET":
                        book = store.get(bid)
                    elif method == "PUT":
                        book = store.update(bid, self._body())
                    elif method == "DELETE":
                        return self._send(204) if store.delete(bid) else self._send(
                            404, {"error": "book not found"})
                    else:
                        return self._send(405, {"error": "method not allowed"})
                    if book is None:
                        return self._send(404, {"error": "book not found"})
                    return self._send(200, book)
                self._send(404, {"error": "not found"})
            except ValidationError as e:
                self._send(400, {"error": str(e)})

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

        def do_PUT(self):
            self._route("PUT")

        def do_DELETE(self):
            self._route("DELETE")

    return Handler


def create_server(host="127.0.0.1", port=8000, db_path=":memory:"):
    return ThreadingHTTPServer((host, port), make_handler(BookStore(db_path)))


if __name__ == "__main__":
    srv = create_server(
        os.environ.get("HOST", "127.0.0.1"),
        int(os.environ.get("PORT", "8000")),
        os.environ.get("DB_PATH", "books.db"),
    )
    print(f"Listening on {srv.server_address[0]}:{srv.server_address[1]}")
    srv.serve_forever()
