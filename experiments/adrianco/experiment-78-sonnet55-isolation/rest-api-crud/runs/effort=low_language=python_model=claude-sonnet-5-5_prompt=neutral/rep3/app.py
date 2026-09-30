"""Book collection REST API using only the Python standard library."""
import json
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

FIELDS = ("title", "author", "year", "isbn")


def init_db(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"
    )
    conn.commit()
    return conn


def validate(data):
    if not isinstance(data, dict):
        return None, "body must be a JSON object"
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            return None, f"{f} is required"
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return None, "year must be an integer"
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "isbn must be a string"
    return {"title": data["title"].strip(), "author": data["author"].strip(),
            "year": year, "isbn": isbn}, None


def make_handler(conn):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body=None):
            payload = json.dumps(body if body is not None else {}).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _body(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"null")
            except (ValueError, UnicodeDecodeError):
                return None

        def _route(self):
            u = urlparse(self.path)
            path = u.path.rstrip("/") or "/"
            m = re.fullmatch(r"/books/(\d+)", path)
            return path, (int(m.group(1)) if m else None), parse_qs(u.query)

        def _get(self, bid):
            return conn.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()

        def do_GET(self):
            path, bid, q = self._route()
            if path == "/health":
                return self._send(200, {"status": "ok"})
            if path == "/books":
                if "author" in q:
                    rows = conn.execute("SELECT * FROM books WHERE author=? ORDER BY id",
                                        (q["author"][0],)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
                return self._send(200, [dict(r) for r in rows])
            if bid is not None:
                row = self._get(bid)
                return self._send(200, dict(row)) if row else self._send(404, {"error": "not found"})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            path, _, _ = self._route()
            if path != "/books":
                return self._send(404, {"error": "not found"})
            book, err = validate(self._body())
            if err:
                return self._send(400, {"error": err})
            cur = conn.execute("INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                               tuple(book[f] for f in FIELDS))
            conn.commit()
            self._send(201, dict(self._get(cur.lastrowid)))

        def do_PUT(self):
            _, bid, _ = self._route()
            if bid is None:
                return self._send(404, {"error": "not found"})
            if not self._get(bid):
                return self._send(404, {"error": "not found"})
            book, err = validate(self._body())
            if err:
                return self._send(400, {"error": err})
            conn.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                         (*[book[f] for f in FIELDS], bid))
            conn.commit()
            self._send(200, dict(self._get(bid)))

        def do_DELETE(self):
            _, bid, _ = self._route()
            if bid is None or not self._get(bid):
                return self._send(404, {"error": "not found"})
            conn.execute("DELETE FROM books WHERE id=?", (bid,))
            conn.commit()
            self._send(200, {"deleted": bid})

    return Handler


def create_server(db_path="books.db", host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), make_handler(init_db(db_path)))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Listening on http://127.0.0.1:{port}")
    create_server(port=port).serve_forever()
