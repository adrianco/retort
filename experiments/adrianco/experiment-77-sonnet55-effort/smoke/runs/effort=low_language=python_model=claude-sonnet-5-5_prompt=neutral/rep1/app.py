"""Book collection REST API using only the Python standard library."""
import json
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

FIELDS = ("title", "author", "year", "isbn")
BOOK_RE = re.compile(r"^/books/(\d+)/?$")


def init_db(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
        "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
    )
    conn.commit()
    return conn


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
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return None, "year must be an integer"
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "isbn must be a string"
    clean["year"] = year
    clean["isbn"] = isbn
    return clean, None


def make_handler(conn):
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

        def _get(self, book_id):
            row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
            return dict(row) if row else None

        def _route(self, method):
            url = urlparse(self.path)
            path = url.path
            if path == "/health" and method == "GET":
                return self._send(200, {"status": "ok"})
            if path.rstrip("/") == "/books":
                if method == "GET":
                    author = parse_qs(url.query).get("author", [None])[0]
                    if author is None:
                        rows = conn.execute("SELECT * FROM books ORDER BY id")
                    else:
                        rows = conn.execute(
                            "SELECT * FROM books WHERE author=? ORDER BY id", (author,))
                    return self._send(200, [dict(r) for r in rows])
                if method == "POST":
                    data, err = self._body()
                    clean, err = (None, err) if err else validate(data)
                    if err:
                        return self._send(400, {"error": err})
                    cur = conn.execute(
                        "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                        tuple(clean[f] for f in FIELDS))
                    conn.commit()
                    return self._send(201, self._get(cur.lastrowid))
                return self._send(405, {"error": "method not allowed"})
            m = BOOK_RE.match(path)
            if m:
                bid = int(m.group(1))
                book = self._get(bid)
                if book is None:
                    return self._send(404, {"error": "book not found"})
                if method == "GET":
                    return self._send(200, book)
                if method == "PUT":
                    data, err = self._body()
                    clean, err = (None, err) if err else validate(data)
                    if err:
                        return self._send(400, {"error": err})
                    conn.execute(
                        "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                        (*[clean[f] for f in FIELDS], bid))
                    conn.commit()
                    return self._send(200, self._get(bid))
                if method == "DELETE":
                    conn.execute("DELETE FROM books WHERE id=?", (bid,))
                    conn.commit()
                    return self._send(204)
                return self._send(405, {"error": "method not allowed"})
            self._send(404, {"error": "not found"})

        def do_GET(self): self._route("GET")
        def do_POST(self): self._route("POST")
        def do_PUT(self): self._route("PUT")
        def do_DELETE(self): self._route("DELETE")

    return Handler


def create_server(db_path="books.db", host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), make_handler(init_db(db_path)))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = create_server(port=port)
    print(f"Listening on http://127.0.0.1:{port}")
    srv.serve_forever()
