"""Book collection REST API.

Pure standard library: a WSGI application backed by SQLite.
Run with ``python app.py`` (see README.md).
"""
import json
import os
import re
import sqlite3
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB", "books.db")
MAX_BODY_BYTES = 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

STATUS_TEXT = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    413: "Payload Too Large",
    500: "Internal Server Error",
}

BOOK_PATH = re.compile(r"^/books/(\d+)$")


class HTTPError(Exception):
    def __init__(self, status, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []


def validate_book(payload):
    """Return a cleaned book dict, or raise HTTPError(400) listing all problems."""
    if not isinstance(payload, dict):
        raise HTTPError(400, "Request body must be a JSON object")

    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            cleaned[field] = value.strip()

    year = payload.get("year")
    if year is None:
        cleaned["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    else:
        cleaned["year"] = year

    isbn = payload.get("isbn")
    if isbn is None:
        cleaned["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        cleaned["isbn"] = isbn.strip() or None

    if errors:
        raise HTTPError(400, "Validation failed", details=errors)
    return cleaned


def row_to_book(row):
    return {k: row[k] for k in ("id", "title", "author", "year", "isbn")}


class BookAPI:
    """WSGI application. A new SQLite connection is used per request, which
    keeps it safe under threaded servers."""

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        # Keep a single connection open for in-memory DBs, otherwise each
        # request would see a fresh, empty database.
        self._shared = None
        if db_path == ":memory:":
            self._shared = self._connect(check_same_thread=False)
            self._shared.execute(SCHEMA)
        else:
            with self._connect() as conn:
                conn.execute(SCHEMA)

    def _connect(self, **kwargs):
        conn = sqlite3.connect(self.db_path, **kwargs)
        conn.row_factory = sqlite3.Row
        return conn

    # -- WSGI entry point -------------------------------------------------
    def __call__(self, environ, start_response):
        try:
            status, body, headers = self._dispatch(environ)
        except HTTPError as exc:
            payload = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
            status, body, headers = exc.status, payload, exc.headers
        except Exception:  # pragma: no cover - last-resort guard
            status, body, headers = 500, {"error": "Internal server error"}, []
        return self._respond(start_response, status, body, headers)

    @staticmethod
    def _respond(start_response, status, body, headers):
        data = b"" if body is None else json.dumps(body).encode("utf-8")
        out_headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(data))),
        ] + list(headers)
        start_response(f"{status} {STATUS_TEXT.get(status, '')}".strip(), out_headers)
        return [data]

    # -- routing ------------------------------------------------------------
    def _dispatch(self, environ):
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO", "") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            self._require(method, ("GET",))
            return 200, {"status": "ok"}, []

        if path == "/books":
            self._require(method, ("GET", "POST"))
            if method == "POST":
                return self._create(environ)
            return self._list(environ)

        match = BOOK_PATH.match(path)
        if match:
            self._require(method, ("GET", "PUT", "DELETE"))
            book_id = int(match.group(1))
            if method == "GET":
                return self._get(book_id)
            if method == "PUT":
                return self._update(book_id, environ)
            return self._delete(book_id)

        raise HTTPError(404, "Not found")

    @staticmethod
    def _require(method, allowed):
        if method not in allowed:
            raise HTTPError(
                405, "Method not allowed", headers=[("Allow", ", ".join(allowed))]
            )

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HTTPError(400, "Invalid Content-Length")
        if length > MAX_BODY_BYTES:
            raise HTTPError(413, "Request body too large")
        raw = environ["wsgi.input"].read(length) if length else b""
        if not raw:
            raise HTTPError(400, "Request body must be valid JSON")
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, "Request body must be valid JSON")

    def _run(self, fn):
        """Run fn(conn) in a transaction on the appropriate connection."""
        if self._shared is not None:
            with self._shared:
                return fn(self._shared)
        conn = self._connect()
        try:
            with conn:
                return fn(conn)
        finally:
            conn.close()

    def _fetch(self, conn, book_id):
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise HTTPError(404, "Book not found")
        return row_to_book(row)

    # -- handlers -----------------------------------------------------------
    def _create(self, environ):
        book = validate_book(self._read_json(environ))

        def op(conn):
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            return self._fetch(conn, cur.lastrowid)

        created = self._run(op)
        return 201, created, [("Location", f"/books/{created['id']}")]

    def _list(self, environ):
        query = parse_qs(environ.get("QUERY_STRING", ""))
        author = query.get("author", [None])[0]

        def op(conn):
            if author is not None:
                rows = conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            return [row_to_book(r) for r in rows]

        return 200, self._run(op), []

    def _get(self, book_id):
        return 200, self._run(lambda conn: self._fetch(conn, book_id)), []

    def _update(self, book_id, environ):
        book = validate_book(self._read_json(environ))

        def op(conn):
            self._fetch(conn, book_id)
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            return self._fetch(conn, book_id)

        return 200, self._run(op), []

    def _delete(self, book_id):
        def op(conn):
            self._fetch(conn, book_id)
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))

        self._run(op)
        return 204, None, []


def create_app(db_path=None):
    return BookAPI(db_path or DEFAULT_DB_PATH)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    app = create_app()
    with make_server(host, port, app) as server:
        print(f"Serving on http://{host}:{port} (db: {app.db_path})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
