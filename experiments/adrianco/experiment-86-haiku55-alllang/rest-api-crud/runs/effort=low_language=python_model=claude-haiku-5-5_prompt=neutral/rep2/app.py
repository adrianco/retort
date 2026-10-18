"""REST API for managing a book collection, backed by SQLite.

Built on the standard library (http.server + sqlite3) so it runs without
installing any third-party packages.
"""

import json
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_DB_PATH = "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""

BOOK_PATH = re.compile(r"^/books/(\d+)$")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class Store:
    """Thin SQLite wrapper. Each call opens its own connection, which keeps
    things safe under the threaded HTTP server."""

    def __init__(self, path=DEFAULT_DB_PATH):
        self.path = path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _write(self, sql, params=()):
        """Run a write statement and return (lastrowid, rowcount)."""
        conn = self._connect()
        try:
            with conn:  # commits on success, rolls back on error
                cur = conn.execute(sql, params)
                return cur.lastrowid, cur.rowcount
        finally:
            conn.close()

    def _read(self, sql, params=(), one=False):
        conn = self._connect()
        try:
            cur = conn.execute(sql, params)
            if one:
                row = cur.fetchone()
                return _row_to_book(row) if row else None
            return [_row_to_book(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def create(self, data):
        book_id, _ = self._write(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        return self.get(book_id)

    def get(self, book_id):
        return self._read("SELECT * FROM books WHERE id = ?", (book_id,), one=True)

    def list(self, author=None):
        if author is None:
            return self._read("SELECT * FROM books ORDER BY id")
        return self._read(
            "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
            (author,),
        )

    def update(self, book_id, data):
        existing = self.get(book_id)
        if existing is None:
            return None
        merged = {**existing, **data}
        self._write(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
        )
        return self.get(book_id)

    def delete(self, book_id):
        _, rowcount = self._write("DELETE FROM books WHERE id = ?", (book_id,))
        return rowcount > 0


def _row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book(data, partial=False):
    """Validate and normalise a book payload. Returns the cleaned dict.

    When partial is True (PUT), absent fields are allowed; present fields
    must still be valid.
    """
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    clean = {}

    for field in ("title", "author"):
        if field not in data:
            if not partial:
                errors[field] = "is required"
            continue
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            errors[field] = "must be a non-empty string"
        else:
            clean[field] = value.strip()

    if "year" in data and data["year"] is not None:
        year = data["year"]
        if isinstance(year, bool) or not isinstance(year, int) or year < 0 or year > 9999:
            errors["year"] = "must be an integer between 0 and 9999"
        else:
            clean["year"] = year
    elif "year" in data:
        clean["year"] = None
    else:
        clean.setdefault("year", None)

    if "isbn" in data and data["isbn"] is not None:
        isbn = data["isbn"]
        if not isinstance(isbn, str) or not isbn.strip():
            errors["isbn"] = "must be a non-empty string"
        else:
            clean["isbn"] = isbn.strip()
    else:
        clean.setdefault("isbn", None)

    if errors:
        raise ValidationError(errors)
    return clean


def make_handler(store):
    class BookHandler(BaseHTTPRequestHandler):
        server_version = "BooksAPI/1.0"

        # --- helpers -----------------------------------------------------

        def _send(self, status, payload=None):
            body = b"" if payload is None else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _error(self, status, message, details=None):
            payload = {"error": message}
            if details is not None:
                payload["details"] = details
            self._send(status, payload)

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                return json.loads(raw.decode("utf-8") or "null")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValidationError({"body": "must be valid JSON"})

        def _route(self):
            """Return (handler_name, book_id) or (None, None) if unmatched."""
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path == "/health":
                return "health", None
            if path == "/books":
                return "books", None
            match = BOOK_PATH.match(path)
            if match:
                return "book", int(match.group(1))
            return None, None

        def _dispatch(self, method):
            name, book_id = self._route()
            allowed = {
                "health": ("GET",),
                "books": ("GET", "POST"),
                "book": ("GET", "PUT", "DELETE"),
            }
            if name is None:
                return self._error(404, "not found")
            if method not in allowed[name]:
                return self._error(405, "method not allowed")

            try:
                handler = getattr(self, f"_{method.lower()}_{name}")
                if book_id is None:
                    handler()
                else:
                    handler(book_id)
            except ValidationError as exc:
                self._error(400, "validation failed", exc.errors)
            except sqlite3.Error:
                self._error(500, "database error")

        # --- verbs -------------------------------------------------------

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def do_PUT(self):
            self._dispatch("PUT")

        def do_DELETE(self):
            self._dispatch("DELETE")

        def do_PATCH(self):
            # Not supported, but routed through dispatch so the reply is JSON 405.
            self._dispatch("PATCH")

        # --- endpoints ---------------------------------------------------

        def _get_health(self):
            self._send(200, {"status": "ok"})

        def _get_books(self):
            query = parse_qs(urlparse(self.path).query)
            author = query.get("author", [None])[0]
            self._send(200, store.list(author=author))

        def _post_books(self):
            data = validate_book(self._read_json())
            self._send(201, store.create(data))

        def _get_book(self, book_id):
            book = store.get(book_id)
            if book is None:
                return self._error(404, "book not found")
            self._send(200, book)

        def _put_book(self, book_id):
            data = validate_book(self._read_json(), partial=True)
            book = store.update(book_id, data)
            if book is None:
                return self._error(404, "book not found")
            self._send(200, book)

        def _delete_book(self, book_id):
            if not store.delete(book_id):
                return self._error(404, "book not found")
            self._send(204)

        def log_message(self, fmt, *args):  # keep test output quiet
            if getattr(self.server, "verbose", False):
                super().log_message(fmt, *args)

    return BookHandler


def create_server(host="127.0.0.1", port=8000, db_path=DEFAULT_DB_PATH, verbose=False):
    store = Store(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(store))
    server.verbose = verbose
    return server


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = create_server(port=port, verbose=True)
    print(f"Serving books API on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
