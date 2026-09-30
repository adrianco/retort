"""Book collection REST API using only the standard library (http.server + sqlite3)."""
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
                "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,"
                "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
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
    """Return (clean, errors)."""
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
                length = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(length) or b"null"), None
            except (ValueError, UnicodeDecodeError):
                return None, "invalid JSON body"

        def _route(self):
            url = urlparse(self.path)
            path = url.path.rstrip("/") or "/"
            m = re.fullmatch(r"/books/(\d+)", path)
            return path, (int(m.group(1)) if m else None), parse_qs(url.query)

        def do_GET(self):
            path, bid, qs = self._route()
            if path == "/health":
                return self._send(200, {"status": "ok"})
            if path == "/books":
                return self._send(200, store.list(qs.get("author", [None])[0]))
            if bid is not None:
                book = store.get(bid)
                return self._send(200, book) if book else self._send(404, {"error": "book not found"})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            path, _, _ = self._route()
            if path != "/books":
                return self._send(404, {"error": "not found"})
            data, err = self._body()
            if err:
                return self._send(400, {"error": err})
            clean, errors = validate(data)
            if errors:
                return self._send(400, {"error": "validation failed", "details": errors})
            self._send(201, store.create(clean))

        def do_PUT(self):
            _, bid, _ = self._route()
            if bid is None:
                return self._send(404, {"error": "not found"})
            data, err = self._body()
            if err:
                return self._send(400, {"error": err})
            clean, errors = validate(data)
            if errors:
                return self._send(400, {"error": "validation failed", "details": errors})
            book = store.update(bid, clean)
            self._send(200, book) if book else self._send(404, {"error": "book not found"})

        def do_DELETE(self):
            _, bid, _ = self._route()
            if bid is None:
                return self._send(404, {"error": "not found"})
            if store.delete(bid):
                self._send(204)
            else:
                self._send(404, {"error": "book not found"})

    return Handler


def create_server(host="127.0.0.1", port=8000, db_path=":memory:"):
    return ThreadingHTTPServer((host, port), make_handler(BookStore(db_path)))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    srv = create_server(port=port, db_path=os.environ.get("DB_PATH", "books.db"))
    print(f"Listening on http://127.0.0.1:{port}")
    srv.serve_forever()
