"""Book collection REST API: standard-library WSGI app backed by SQLite."""

import json
import os
import re
import sqlite3
from contextlib import closing
from urllib.parse import parse_qs
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
        self.db_path = db_path
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )"""
            )

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- WSGI entry point ---

    def __call__(self, environ, start_response):
        try:
            status, payload = self._route(environ)
        except ApiError as e:
            status = e.status
            payload = {"error": e.message}
            if e.details:
                payload["details"] = e.details
        except Exception:
            status, payload = 500, {"error": "internal server error"}
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = [("Content-Length", str(len(body)))]
        if body:
            headers.append(("Content-Type", "application/json"))
        start_response(STATUS[status], headers)
        return [body]

    def _route(self, environ):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "")
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            self._allow(method, "GET")
            return 200, {"status": "ok"}
        if path == "/books":
            self._allow(method, "GET", "POST")
            if method == "GET":
                query = parse_qs(environ.get("QUERY_STRING", ""))
                return 200, self.list_books(query.get("author", [None])[0])
            return 201, self.create_book(self._read_json(environ))
        match = BOOK_PATH.match(path)
        if match:
            self._allow(method, "GET", "PUT", "DELETE")
            book_id = int(match.group(1))
            if method == "GET":
                return 200, self.get_book(book_id)
            if method == "PUT":
                return 200, self.update_book(book_id, self._read_json(environ))
            self.delete_book(book_id)
            return 204, None
        raise ApiError(404, "not found")

    @staticmethod
    def _allow(method, *allowed):
        if method not in allowed:
            raise ApiError(405, "method not allowed")

    @staticmethod
    def _read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise ApiError(400, "invalid Content-Length")
        if length > MAX_BODY:
            raise ApiError(400, "request body too large")
        raw = environ["wsgi.input"].read(length) if length > 0 else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "request body must be valid JSON")

    # --- data operations ---

    def list_books(self, author=None):
        sql, params = "SELECT * FROM books", ()
        if author is not None:
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        with closing(self._connect()) as conn:
            return [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]

    def get_book(self, book_id):
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise ApiError(404, "book not found")
        return dict(row)

    def create_book(self, data):
        book = validate_book(data)
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
        return {"id": cur.lastrowid, **book}

    def update_book(self, book_id, data):
        book = validate_book(data)
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
        if cur.rowcount == 0:
            raise ApiError(404, "book not found")
        return {"id": book_id, **book}

    def delete_book(self, book_id):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cur.rowcount == 0:
            raise ApiError(404, "book not found")


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    app = BookApp(os.environ.get("BOOKS_DB", "books.db"))
    with make_server(host, port, app) as server:
        print(f"Serving on http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
