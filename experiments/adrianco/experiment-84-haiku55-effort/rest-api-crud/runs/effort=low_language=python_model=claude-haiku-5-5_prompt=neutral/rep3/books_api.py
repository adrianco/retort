"""REST API for managing a book collection, backed by SQLite.

Built on the standard library only (http.server + sqlite3) so it runs
without installing third-party packages.

Run:  python books_api.py [--host 127.0.0.1] [--port 8000] [--db books.db]
"""

import argparse
import json
import re
import sqlite3
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_BODY_BYTES = 1_000_000
BOOK_ID_PATTERN = re.compile(r"^/books/(\d+)$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
)
"""


class ValidationError(Exception):
    """Raised when a request payload fails validation."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


class ConflictError(Exception):
    """Raised when a write violates a uniqueness constraint."""


class BookStore:
    """Thin SQLite-backed repository for books.

    A single connection is shared across request threads and guarded by a lock.
    """

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def _execute(self, sql, params=()):
        with self._lock:
            try:
                cur = self._conn.execute(sql, params)
                self._conn.commit()
                return cur
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                raise ConflictError("a book with this ISBN already exists") from exc

    def create(self, data):
        cur = self._execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data["year"], data["isbn"]),
        )
        return self.get(cur.lastrowid)

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, author=None):
        sql = "SELECT * FROM books"
        params = ()
        if author is not None:
            sql += " WHERE LOWER(author) = LOWER(?)"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update(self, book_id, data):
        cur = self._execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data["year"], data["isbn"], book_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get(book_id)

    def delete(self, book_id):
        cur = self._execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0


def validate_book(payload):
    """Validate a book payload and return a normalised dict.

    title and author are required non-empty strings. year is an optional
    integer between 0 and 9999. isbn is an optional non-empty string.
    """
    if not isinstance(payload, dict):
        raise ValidationError(["request body must be a JSON object"])

    errors = []
    clean = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"'{field}' is required and must be a non-empty string")
        else:
            clean[field] = value.strip()

    year = payload.get("year")
    if year is None:
        clean["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int) or not 0 <= year <= 9999:
        errors.append("'year' must be an integer between 0 and 9999")
    else:
        clean["year"] = year

    isbn = payload.get("isbn")
    if isbn is None:
        clean["isbn"] = None
    elif not isinstance(isbn, str) or not isbn.strip():
        errors.append("'isbn' must be a non-empty string when provided")
    else:
        clean["isbn"] = isbn.strip()

    if errors:
        raise ValidationError(errors)
    return clean


def make_handler(store):
    """Build a request handler class bound to a BookStore instance."""

    class BookHandler(BaseHTTPRequestHandler):
        server_version = "BooksAPI/1.0"

        # --- helpers -------------------------------------------------------

        def _send_json(self, status, body, headers=None):
            raw = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(raw)

        def _send_error_json(self, status, message, details=None):
            body = {"error": message}
            if details:
                body["details"] = details
            self._send_json(status, body)

        def _read_json(self):
            length = self.headers.get("Content-Length")
            if length is None:
                raise ValidationError(["request body is required"])
            try:
                length = int(length)
            except ValueError:
                raise ValidationError(["invalid Content-Length header"])
            if length <= 0:
                raise ValidationError(["request body is required"])
            if length > MAX_BODY_BYTES:
                raise ValidationError(["request body too large"])
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValidationError(["request body must be valid JSON"])

        def _parse_path(self):
            parsed = urlparse(self.path)
            return parsed.path.rstrip("/") or "/", parse_qs(parsed.query)

        def _book_id(self, path):
            match = BOOK_ID_PATTERN.match(path)
            return int(match.group(1)) if match else None

        def _handle_error(self, exc):
            if isinstance(exc, ValidationError):
                self._send_error_json(HTTPStatus.BAD_REQUEST, "validation failed", exc.errors)
            elif isinstance(exc, ConflictError):
                self._send_error_json(HTTPStatus.CONFLICT, str(exc))
            else:
                self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

        def _dispatch(self, action):
            try:
                action()
            except (ValidationError, ConflictError) as exc:
                self._handle_error(exc)
            except Exception:  # pragma: no cover - defensive catch-all
                self.log_error("unhandled error serving %s", self.path, exc_info=True)
                self._handle_error(RuntimeError())

        # --- routes --------------------------------------------------------

        def do_GET(self):
            self._dispatch(self._get)

        def do_POST(self):
            self._dispatch(self._post)

        def do_PUT(self):
            self._dispatch(self._put)

        def do_DELETE(self):
            self._dispatch(self._delete)

        def _get(self):
            path, query = self._parse_path()
            if path == "/health":
                return self._send_json(HTTPStatus.OK, {"status": "ok"})
            if path == "/books":
                author = query.get("author", [None])[0]
                return self._send_json(HTTPStatus.OK, store.list(author=author))
            book_id = self._book_id(path)
            if book_id is not None:
                book = store.get(book_id)
                if book is None:
                    return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
                return self._send_json(HTTPStatus.OK, book)
            return self._send_error_json(HTTPStatus.NOT_FOUND, "route not found")

        def _post(self):
            path, _ = self._parse_path()
            if path != "/books":
                return self._send_error_json(HTTPStatus.NOT_FOUND, "route not found")
            data = validate_book(self._read_json())
            book = store.create(data)
            return self._send_json(
                HTTPStatus.CREATED,
                book,
                headers={"Location": f"/books/{book['id']}"},
            )

        def _put(self):
            path, _ = self._parse_path()
            book_id = self._book_id(path)
            if book_id is None:
                return self._send_error_json(HTTPStatus.NOT_FOUND, "route not found")
            data = validate_book(self._read_json())
            book = store.update(book_id, data)
            if book is None:
                return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
            return self._send_json(HTTPStatus.OK, book)

        def _delete(self):
            path, _ = self._parse_path()
            book_id = self._book_id(path)
            if book_id is None:
                return self._send_error_json(HTTPStatus.NOT_FOUND, "route not found")
            if not store.delete(book_id):
                return self._send_error_json(HTTPStatus.NOT_FOUND, "book not found")
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format, *args):  # keep test output quiet
            pass

    return BookHandler


def create_server(host="127.0.0.1", port=8000, db_path="books.db"):
    """Create (but do not start) an HTTP server for the books API."""
    store = BookStore(db_path)
    return ThreadingHTTPServer((host, port), make_handler(store))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Books REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="path to the SQLite database file")
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port, args.db)
    print(f"Books API listening on http://{args.host}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
