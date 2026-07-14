"""A small REST API for managing a book collection.

Built with the Python standard library only (http.server + sqlite3) so it has
no external dependencies. Use ``make_app()`` to build a WSGI-style request
handler bound to a specific database, or run this module directly to start a
server.
"""

import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_DB = "books.db"


def init_db(db_path):
    """Create the books table if it does not already exist and return a
    connection to ``db_path``."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )
        """
    )
    conn.commit()
    return conn


def _row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate(payload):
    """Validate a create/update payload. Returns (clean_data, error)."""
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"

    title = payload.get("title")
    author = payload.get("author")

    if not isinstance(title, str) or not title.strip():
        return None, "Field 'title' is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return None, "Field 'author' is required and must be a non-empty string"

    year = payload.get("year")
    if year is not None and not isinstance(year, int):
        return None, "Field 'year' must be an integer"

    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "Field 'isbn' must be a string"

    return {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn,
    }, None


class BookHandler(BaseHTTPRequestHandler):
    # ``conn`` is injected by make_app() via a subclass attribute.
    conn = None

    # ---- helpers -------------------------------------------------------
    def _send(self, status, body=None):
        payload = b"" if body is None else json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return None, "Request body is required"
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8")), None
        except (ValueError, UnicodeDecodeError):
            return None, "Request body must be valid JSON"

    def log_message(self, *args):  # silence default stderr logging
        pass

    # ---- routing -------------------------------------------------------
    def _match_id(self, path):
        m = re.fullmatch(r"/books/(\d+)", path)
        return int(m.group(1)) if m else None

    def do_GET(self):
        path, _, query = self.path.partition("?")

        if path == "/health":
            self._send(200, {"status": "ok"})
            return

        if path == "/books":
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            author = params.get("author")
            if author is not None:
                from urllib.parse import unquote

                author = unquote(author)
                rows = self.conn.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT * FROM books ORDER BY id"
                ).fetchall()
            self._send(200, [_row_to_dict(r) for r in rows])
            return

        book_id = self._match_id(path)
        if book_id is not None:
            row = self.conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if row is None:
                self._send(404, {"error": "Book not found"})
            else:
                self._send(200, _row_to_dict(row))
            return

        self._send(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/books":
            self._send(404, {"error": "Not found"})
            return

        payload, err = self._read_json()
        if err:
            self._send(400, {"error": err})
            return

        data, err = _validate(payload)
        if err:
            self._send(400, {"error": err})
            return

        cur = self.conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        self._send(201, _row_to_dict(row))

    def do_PUT(self):
        book_id = self._match_id(self.path)
        if book_id is None:
            self._send(404, {"error": "Not found"})
            return

        existing = self.conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            self._send(404, {"error": "Book not found"})
            return

        payload, err = self._read_json()
        if err:
            self._send(400, {"error": err})
            return

        data, err = _validate(payload)
        if err:
            self._send(400, {"error": err})
            return

        self.conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        self._send(200, _row_to_dict(row))

    def do_DELETE(self):
        book_id = self._match_id(self.path)
        if book_id is None:
            self._send(404, {"error": "Not found"})
            return

        cur = self.conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.conn.commit()
        if cur.rowcount == 0:
            self._send(404, {"error": "Book not found"})
        else:
            self._send(204)


def make_app(db_path=DEFAULT_DB):
    """Return a handler class bound to a freshly initialised database."""
    conn = init_db(db_path)

    class BoundHandler(BookHandler):
        pass

    BoundHandler.conn = conn
    return BoundHandler


def serve(host="127.0.0.1", port=8000, db_path=DEFAULT_DB):
    handler = make_app(db_path)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving book API on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    serve()
