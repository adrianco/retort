"""REST API for managing a book collection, backed by SQLite.

Built on the standard library only (http.server + sqlite3), so it runs
anywhere Python 3.8+ is installed with no third-party dependencies.

Run:
    python books_api.py --port 8000 --db books.db
"""

import argparse
import json
import re
import sqlite3
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""

BOOK_FIELDS = ("title", "author", "year", "isbn")
MAX_BODY_BYTES = 1_000_000


class ValidationError(ValueError):
    """Raised when a request payload fails validation."""


def validate_book(data, partial=False):
    """Validate a book payload and return a cleaned dict of known fields.

    With partial=False (create), title and author are required.
    With partial=True (update), only the fields present are validated.
    """
    if not isinstance(data, dict):
        raise ValidationError("request body must be a JSON object")

    unknown = set(data) - set(BOOK_FIELDS)
    if unknown:
        raise ValidationError(f"unknown field(s): {', '.join(sorted(unknown))}")

    cleaned = {}
    for field in ("title", "author"):
        if field not in data:
            if not partial:
                raise ValidationError(f"'{field}' is required")
            continue
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"'{field}' must be a non-empty string")
        cleaned[field] = value.strip()

    if "year" in data:
        year = data["year"]
        if year is None:
            cleaned["year"] = None
        elif isinstance(year, bool) or not isinstance(year, int):
            raise ValidationError("'year' must be an integer")
        elif year < 0 or year > 9999:
            raise ValidationError("'year' must be between 0 and 9999")
        else:
            cleaned["year"] = year

    if "isbn" in data:
        isbn = data["isbn"]
        if isbn is None:
            cleaned["isbn"] = None
        elif not isinstance(isbn, str) or not re.fullmatch(r"[0-9Xx\- ]{10,20}", isbn):
            raise ValidationError("'isbn' must be a 10- or 13-character ISBN string")
        else:
            cleaned["isbn"] = isbn.strip()

    if not partial and not cleaned:
        raise ValidationError("request body must not be empty")
    return cleaned


class BookStore:
    """Thin data-access layer around a SQLite database file."""

    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        # A single shared connection, guarded by a lock, keeps ":memory:"
        # databases consistent across request threads.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self):
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_dict(row):
        return {key: row[key] for key in ("id", "title", "author", "year", "isbn")}

    def create(self, data):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn")),
            )
            book_id = cur.lastrowid
        return self.get(book_id)

    def list(self, author=None):
        query = "SELECT * FROM books"
        params = []
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params.append(author)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def update(self, book_id, data):
        if not data:
            return self.get(book_id)
        assignments = ", ".join(f"{field} = ?" for field in data)
        params = list(data.values()) + [book_id]
        with self._lock, self._conn:
            cur = self._conn.execute(f"UPDATE books SET {assignments} WHERE id = ?", params)
            updated = cur.rowcount
        return self.get(book_id) if updated else None

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()


_BOOK_PATH = re.compile(r"^/books/(\d+)$")


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BooksAPI/1.0"

    # Set on the server instance by create_server().
    store: BookStore

    # ---- response helpers -------------------------------------------------

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status, message):
        self._send_json(status, {"error": message})

    def _read_json(self):
        length = self.headers.get("Content-Length")
        if length is None:
            raise ValidationError("request body is required")
        try:
            size = int(length)
        except ValueError:
            raise ValidationError("invalid Content-Length header")
        if size <= 0:
            raise ValidationError("request body is required")
        if size > MAX_BODY_BYTES:
            raise _PayloadTooLarge()
        raw = self.rfile.read(size)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("request body must be valid JSON")

    def _route(self):
        """Return (path, query_dict) or send 404 and return None."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        return path, parse_qs(parsed.query)

    def _book_id(self, path):
        match = _BOOK_PATH.match(path)
        return int(match.group(1)) if match else None

    # ---- dispatch ---------------------------------------------------------

    def _dispatch(self, method):
        try:
            path, query = self._route()
            if path == "/health":
                return self._health(method)
            if path == "/books":
                if method == "GET":
                    return self._list_books(query)
                if method == "POST":
                    return self._create_book()
                return self._method_not_allowed("GET, POST")
            book_id = self._book_id(path)
            if book_id is not None:
                if method == "GET":
                    return self._get_book(book_id)
                if method == "PUT":
                    return self._update_book(book_id)
                if method == "DELETE":
                    return self._delete_book(book_id)
                return self._method_not_allowed("GET, PUT, DELETE")
            return self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
        except _PayloadTooLarge:
            self._send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
        except ValidationError as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        # Not supported; routed through dispatch so the client gets a JSON 405.
        self._dispatch("PATCH")

    # ---- handlers ---------------------------------------------------------

    def _health(self, method):
        if method != "GET":
            return self._method_not_allowed("GET")
        try:
            self.store.ping()
        except sqlite3.Error as exc:
            return self._send_json(HTTPStatus.SERVICE_UNAVAILABLE,
                                   {"status": "unhealthy", "error": str(exc)})
        return self._send_json(HTTPStatus.OK, {"status": "ok"})

    def _list_books(self, query):
        author = query.get("author", [None])[0]
        if author is not None and not author.strip():
            raise ValidationError("'author' filter must not be empty")
        books = self.store.list(author=author.strip() if author else None)
        return self._send_json(HTTPStatus.OK, books)

    def _create_book(self):
        data = validate_book(self._read_json())
        book = self.store.create(data)
        return self._send_json(HTTPStatus.CREATED, book)

    def _get_book(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
        return self._send_json(HTTPStatus.OK, book)

    def _update_book(self, book_id):
        data = validate_book(self._read_json(), partial=True)
        book = self.store.update(book_id, data)
        if book is None:
            return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
        return self._send_json(HTTPStatus.OK, book)

    def _delete_book(self, book_id):
        if not self.store.delete(book_id):
            return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _method_not_allowed(self, allowed):
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", allowed)
        self.send_header("Content-Type", "application/json")
        body = json.dumps({"error": "method not allowed"}).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # keep test output quiet
        pass


class _PayloadTooLarge(Exception):
    pass


def create_server(host="127.0.0.1", port=8000, db_path="books.db"):
    """Build (but do not start) an HTTP server bound to the given database."""
    store = BookStore(db_path)
    handler = type("Handler", (BookRequestHandler,), {"store": store})
    server = ThreadingHTTPServer((host, port), handler)
    server.book_store = store
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Books REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="path to SQLite database file")
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port, args.db)
    print(f"Books API listening on http://{args.host}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.book_store.close()


if __name__ == "__main__":
    main()
