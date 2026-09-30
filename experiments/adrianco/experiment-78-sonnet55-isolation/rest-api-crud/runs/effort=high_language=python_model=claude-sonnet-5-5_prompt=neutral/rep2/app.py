"""Book collection REST API.

Pure standard library: a WSGI application backed by SQLite. Run with
``python app.py`` (uses wsgiref's development server).
"""
import json
import os
import re
import sqlite3
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

DEFAULT_DB = os.environ.get("BOOKS_DB", "books.db")
MAX_BODY = 1024 * 1024

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

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


class HTTPError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def validate_book(data):
    """Validate and normalise a book payload; raise HTTPError(400) on problems."""
    if not isinstance(data, dict):
        raise HTTPError(400, "Request body must be a JSON object")

    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            cleaned[field] = value.strip()

    year = data.get("year")
    if year is None:
        cleaned["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    else:
        cleaned["year"] = year

    isbn = data.get("isbn")
    if isbn is None:
        cleaned["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        cleaned["isbn"] = isbn.strip() or None

    if errors:
        raise HTTPError(400, "Validation failed", errors)
    return cleaned


def row_to_dict(row):
    return {k: row[k] for k in row.keys()}


class BookApp:
    """WSGI application. Each request opens its own SQLite connection."""

    ROUTE_COLLECTION = re.compile(r"^/books/?$")
    ROUTE_ITEM = re.compile(r"^/books/([^/]+)/?$")

    def __init__(self, db_path=None):
        self.db_path = db_path or DEFAULT_DB
        conn = self._connect()
        try:
            with conn:
                conn.execute(SCHEMA)
        finally:
            conn.close()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # -- WSGI entry point -------------------------------------------------
    def __call__(self, environ, start_response):
        try:
            status, payload = self.dispatch(environ)
        except HTTPError as exc:
            body = {"error": exc.message}
            if exc.details:
                body["details"] = exc.details
            status, payload = exc.status, body
        except Exception:  # pragma: no cover - defensive
            status, payload = 500, {"error": "Internal server error"}

        if payload is None:
            data = b""
            headers = []
        else:
            data = json.dumps(payload).encode("utf-8")
            headers = [("Content-Type", "application/json")]
        headers.append(("Content-Length", str(len(data))))
        start_response(f"{status} {STATUS_TEXT.get(status, '')}", headers)
        return [data]

    # -- routing ----------------------------------------------------------
    def dispatch(self, environ):
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO", "") or "/"

        if path == "/health":
            self._allow(method, ("GET",))
            return 200, {"status": "ok"}

        if self.ROUTE_COLLECTION.match(path):
            self._allow(method, ("GET", "POST"))
            if method == "POST":
                return self.create_book(self._read_json(environ))
            return self.list_books(environ.get("QUERY_STRING", ""))

        m = self.ROUTE_ITEM.match(path)
        if m:
            self._allow(method, ("GET", "PUT", "DELETE"))
            book_id = self._parse_id(m.group(1))
            if method == "GET":
                return self.get_book(book_id)
            if method == "PUT":
                return self.update_book(book_id, self._read_json(environ))
            return self.delete_book(book_id)

        raise HTTPError(404, "Not found")

    @staticmethod
    def _allow(method, allowed):
        if method not in allowed:
            raise HTTPError(405, "Method not allowed")

    @staticmethod
    def _parse_id(raw):
        # Non-numeric ids can never exist, so treat them as not found.
        if not raw.isascii() or not raw.isdigit():
            raise HTTPError(404, "Book not found")
        return int(raw)

    @staticmethod
    def _read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HTTPError(400, "Invalid Content-Length")
        if length > MAX_BODY:
            raise HTTPError(413, "Request body too large")
        raw = environ["wsgi.input"].read(length) if length else b""
        if not raw:
            raise HTTPError(400, "Request body must be a JSON object")
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, "Invalid JSON")

    # -- handlers ---------------------------------------------------------
    def _fetch(self, conn, book_id):
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise HTTPError(404, "Book not found")
        return row_to_dict(row)

    def create_book(self, data):
        book = validate_book(data)
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    (book["title"], book["author"], book["year"], book["isbn"]),
                )
            return 201, self._fetch(conn, cur.lastrowid)
        finally:
            conn.close()

    def list_books(self, query_string):
        params = parse_qs(query_string)
        sql = "SELECT * FROM books"
        args = []
        if "author" in params:
            sql += " WHERE author = ? COLLATE NOCASE"
            args.append(params["author"][-1])
        sql += " ORDER BY id"
        conn = self._connect()
        try:
            return 200, [row_to_dict(r) for r in conn.execute(sql, args)]
        finally:
            conn.close()

    def get_book(self, book_id):
        conn = self._connect()
        try:
            return 200, self._fetch(conn, book_id)
        finally:
            conn.close()

    def update_book(self, book_id, data):
        book = validate_book(data)
        conn = self._connect()
        try:
            with conn:
                self._fetch(conn, book_id)
                conn.execute(
                    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                    (book["title"], book["author"], book["year"], book["isbn"], book_id),
                )
            return 200, self._fetch(conn, book_id)
        finally:
            conn.close()

    def delete_book(self, book_id):
        conn = self._connect()
        try:
            with conn:
                self._fetch(conn, book_id)
                conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return 204, None
        finally:
            conn.close()


def create_app(db_path=None):
    return BookApp(db_path)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    app = create_app()
    with make_server(host, port, app) as server:
        print(f"Serving on http://{host}:{port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
