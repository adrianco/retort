"""Book collection REST API using only the Python standard library."""
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
                "CREATE TABLE IF NOT EXISTS books ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
                "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
            )
            self.conn.commit()

    def _get(self, book_id):
        row = self.conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    def create(self, d):
        with self.lock:
            cur = self.conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                (d["title"], d["author"], d["year"], d["isbn"]),
            )
            self.conn.commit()
            return self._get(cur.lastrowid)

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
            return self._get(book_id)

    def update(self, book_id, d):
        with self.lock:
            if not self._get(book_id):
                return None
            self.conn.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                (d["title"], d["author"], d["year"], d["isbn"], book_id),
            )
            self.conn.commit()
            return self._get(book_id)

    def delete(self, book_id):
        with self.lock:
            cur = self.conn.execute("DELETE FROM books WHERE id=?", (book_id,))
            self.conn.commit()
            return cur.rowcount > 0


def validate(data):
    """Return (cleaned, errors)."""
    if not isinstance(data, dict):
        return None, ["body must be a JSON object"]
    errors = []
    out = {}
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{f} is required and must be a non-empty string")
        else:
            out[f] = v.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    out["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    out["isbn"] = isbn
    return out, errors


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body=None):
            payload = json.dumps(body).encode() if body is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(length) or b"null"), None
            except (ValueError, UnicodeDecodeError):
                return None, "invalid JSON"

        def _route(self, method):
            url = urlparse(self.path)
            path = url.path.rstrip("/") or "/"
            if path == "/health" and method == "GET":
                return self._send(200, {"status": "ok"})
            if path == "/books":
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
            m = re.fullmatch(r"/books/(\d+)", path)
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

        def do_GET(self): self._route("GET")
        def do_POST(self): self._route("POST")
        def do_PUT(self): self._route("PUT")
        def do_DELETE(self): self._route("DELETE")

    return Handler


def create_server(host="127.0.0.1", port=8000, db_path=":memory:"):
    return ThreadingHTTPServer((host, port), make_handler(BookStore(db_path)))


if __name__ == "__main__":
    server = create_server(
        os.environ.get("HOST", "127.0.0.1"),
        int(os.environ.get("PORT", "8000")),
        os.environ.get("DB_PATH", "books.db"),
    )
    print(f"Listening on {server.server_address}")
    server.serve_forever()
