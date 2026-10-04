"""Book collection REST API: a dependency-free WSGI app backed by SQLite."""
import json
import os
import re
import sqlite3
import threading
from wsgiref.simple_server import make_server

STATUS = {
    200: "200 OK",
    201: "201 Created",
    204: "204 No Content",
    400: "400 Bad Request",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    500: "500 Internal Server Error",
}
BOOK_PATH = re.compile(r"^/books/(\d+)$")
MAX_BODY = 1024 * 1024


class ApiError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def validate_book(data):
    """Return a cleaned book dict or raise ApiError(400)."""
    if not isinstance(data, dict):
        raise ApiError(400, "request body must be a JSON object")
    errors = {}
    book = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "required, must be a non-empty string"
        else:
            book[field] = value.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    book["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    book["isbn"] = isbn
    if errors:
        raise ApiError(400, "validation failed", errors)
    return book


class BookApp:
    def __init__(self, db_path="books.db"):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )"""
        )
        self._db.commit()

    def close(self):
        self._db.close()

    # --- data access ---

    def _get(self, book_id):
        row = self._db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise ApiError(404, "book not found")
        return dict(row)

    def create_book(self, data):
        book = validate_book(data)
        cur = self._db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book["title"], book["author"], book["year"], book["isbn"]),
        )
        self._db.commit()
        return self._get(cur.lastrowid)

    def list_books(self, author=None):
        if author:
            rows = self._db.execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id", (author,)
            )
        else:
            rows = self._db.execute("SELECT * FROM books ORDER BY id")
        return [dict(r) for r in rows]

    def update_book(self, book_id, data):
        self._get(book_id)
        book = validate_book(data)
        self._db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book["title"], book["author"], book["year"], book["isbn"], book_id),
        )
        self._db.commit()
        return self._get(book_id)

    def delete_book(self, book_id):
        self._get(book_id)
        self._db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self._db.commit()

    # --- HTTP layer ---

    def _read_json(self, environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise ApiError(400, "invalid Content-Length")
        if length > MAX_BODY:
            raise ApiError(400, "request body too large")
        raw = environ["wsgi.input"].read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "request body must be valid JSON")

    def _route(self, environ):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            if method != "GET":
                raise ApiError(405, "method not allowed")
            return 200, {"status": "ok"}

        if path == "/books":
            if method == "GET":
                from urllib.parse import parse_qs

                query = parse_qs(environ.get("QUERY_STRING", ""))
                author = query.get("author", [None])[0]
                return 200, self.list_books(author)
            if method == "POST":
                return 201, self.create_book(self._read_json(environ))
            raise ApiError(405, "method not allowed")

        match = BOOK_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                return 200, self._get(book_id)
            if method == "PUT":
                return 200, self.update_book(book_id, self._read_json(environ))
            if method == "DELETE":
                self.delete_book(book_id)
                return 204, None
            raise ApiError(405, "method not allowed")

        raise ApiError(404, "not found")

    def __call__(self, environ, start_response):
        try:
            with self._lock:
                status, payload = self._route(environ)
        except ApiError as exc:
            status = exc.status
            payload = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
        except Exception:
            self._db.rollback()
            status, payload = 500, {"error": "internal server error"}
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = [("Content-Length", str(len(body)))]
        if body:
            headers.append(("Content-Type", "application/json"))
        start_response(STATUS[status], headers)
        return [body]


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    app = BookApp(os.environ.get("BOOKS_DB", "books.db"))
    with make_server(host, port, app) as server:
        print(f"Serving on http://{host}:{port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    app.close()


if __name__ == "__main__":
    main()
