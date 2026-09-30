"""Book collection REST API using only the Python standard library."""
import json
import os
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("BOOKS_DB", "books.db")
FIELDS = ("title", "author", "year", "isbn")


def init_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
        "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
    )
    conn.commit()
    conn.close()


def validate(data):
    """Return (clean_dict, errors) for a book payload."""
    if not isinstance(data, dict):
        return None, ["body must be a JSON object"]
    errors = []
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{f} is required")
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


def make_handler(db_path):
    lock = threading.Lock()

    def db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

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
                return None, "invalid JSON"

        def _route(self):
            path, _, query = self.path.partition("?")
            path = path.rstrip("/") or "/"
            return path, query

        def _handle(self, method):
            path, query = self._route()
            if path == "/health" and method == "GET":
                return self._send(200, {"status": "ok"})
            if path == "/books" and method == "GET":
                return self._list(query)
            if path == "/books" and method == "POST":
                return self._create()
            m = re.fullmatch(r"/books/(\d+)", path)
            if m:
                bid = int(m.group(1))
                if method == "GET":
                    return self._get(bid)
                if method == "PUT":
                    return self._update(bid)
                if method == "DELETE":
                    return self._delete(bid)
            self._send(404, {"error": "not found"})

        def do_GET(self): self._handle("GET")
        def do_POST(self): self._handle("POST")
        def do_PUT(self): self._handle("PUT")
        def do_DELETE(self): self._handle("DELETE")

        def _list(self, query):
            from urllib.parse import parse_qs
            author = parse_qs(query).get("author", [None])[0]
            sql, args = "SELECT * FROM books", ()
            if author is not None:
                sql, args = sql + " WHERE author = ?", (author,)
            with lock:
                conn = db()
                rows = conn.execute(sql + " ORDER BY id", args).fetchall()
                conn.close()
            self._send(200, [dict(r) for r in rows])

        def _create(self):
            data, err = self._body()
            if err:
                return self._send(400, {"error": err})
            clean, errors = validate(data)
            if errors:
                return self._send(400, {"error": "validation failed", "details": errors})
            with lock:
                conn = db()
                cur = conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                    tuple(clean[f] for f in FIELDS),
                )
                conn.commit()
                conn.close()
            self._send(201, {"id": cur.lastrowid, **clean})

        def _get(self, bid):
            with lock:
                conn = db()
                row = conn.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
                conn.close()
            if row is None:
                return self._send(404, {"error": "book not found"})
            self._send(200, dict(row))

        def _update(self, bid):
            data, err = self._body()
            if err:
                return self._send(400, {"error": err})
            clean, errors = validate(data)
            if errors:
                return self._send(400, {"error": "validation failed", "details": errors})
            with lock:
                conn = db()
                cur = conn.execute(
                    "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                    tuple(clean[f] for f in FIELDS) + (bid,),
                )
                conn.commit()
                conn.close()
            if cur.rowcount == 0:
                return self._send(404, {"error": "book not found"})
            self._send(200, {"id": bid, **clean})

        def _delete(self, bid):
            with lock:
                conn = db()
                cur = conn.execute("DELETE FROM books WHERE id = ?", (bid,))
                conn.commit()
                conn.close()
            if cur.rowcount == 0:
                return self._send(404, {"error": "book not found"})
            self._send(204)

    return Handler


def create_server(host="127.0.0.1", port=8000, db_path=DB_PATH):
    init_db(db_path)
    return ThreadingHTTPServer((host, port), make_handler(db_path))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = create_server(port=port)
    print(f"Listening on http://127.0.0.1:{port}")
    server.serve_forever()
