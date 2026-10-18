"""A small, dependency-free REST API for a SQLite-backed book collection."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit


DEFAULT_DATABASE = os.environ.get("BOOKS_DATABASE", "books.db")
_ID_PATH = re.compile(r"^/books/(\d+)/?$")


class BookStore:
    """SQLite persistence layer. Each operation uses its own connection."""

    def __init__(self, database: str = DEFAULT_DATABASE) -> None:
        self.database = database
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )"""
            )

    @staticmethod
    def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def list(self, author: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if author is None:
                rows = connection.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
        return [self._as_dict(row) for row in rows]

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._as_dict(row) if row else None

    def create(self, book: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"].strip(), book["author"].strip(), book.get("year"), book.get("isbn")),
            )
            row = connection.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._as_dict(row)

    def update(self, book_id: int, book: dict[str, Any]) -> dict[str, Any] | None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"].strip(), book["author"].strip(), book.get("year"), book.get("isbn"), book_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._as_dict(row)

    def delete(self, book_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0


def validate_book(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."
    title, author = payload.get("title"), payload.get("author")
    if not isinstance(title, str) or not title.strip():
        return None, "'title' is required and must be a non-empty string."
    if not isinstance(author, str) or not author.strip():
        return None, "'author' is required and must be a non-empty string."
    year = payload.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return None, "'year' must be an integer or null."
    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "'isbn' must be a string or null."
    return {"title": title, "author": author, "year": year, "isbn": isbn}, None


def make_handler(store: BookStore) -> type[BaseHTTPRequestHandler]:
    def handle_api(method: str, path: str, payload: Any = None) -> tuple[int, Any]:
        parsed = urlsplit(path)
        route = parsed.path.rstrip("/") or "/"
        if method == "GET" and route == "/health":
            return HTTPStatus.OK, {"status": "ok"}
        if method == "GET" and route == "/books":
            author = parse_qs(parsed.query).get("author", [None])[0]
            return HTTPStatus.OK, store.list(author)
        if method == "POST" and route == "/books":
            book, error = validate_book(payload)
            if error:
                return HTTPStatus.BAD_REQUEST, {"error": error}
            return HTTPStatus.CREATED, store.create(book)
        match = _ID_PATH.fullmatch(parsed.path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                book = store.get(book_id)
                return (HTTPStatus.OK, book) if book else (HTTPStatus.NOT_FOUND, {"error": "Book not found."})
            if method == "PUT":
                book, error = validate_book(payload)
                if error:
                    return HTTPStatus.BAD_REQUEST, {"error": error}
                updated = store.update(book_id, book)
                return (HTTPStatus.OK, updated) if updated else (HTTPStatus.NOT_FOUND, {"error": "Book not found."})
            if method == "DELETE":
                if store.delete(book_id):
                    return HTTPStatus.NO_CONTENT, None
                return HTTPStatus.NOT_FOUND, {"error": "Book not found."}
        return HTTPStatus.NOT_FOUND, {"error": "Route not found."}

    class BooksHandler(BaseHTTPRequestHandler):
        server_version = "BooksAPI/1.0"

        def _send(self, status: int, payload: Any = None) -> None:
            data = b"" if payload is None else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            if payload is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)

        def _body(self) -> Any:
            raw_length = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("Invalid Content-Length.") from exc
            if length <= 0:
                raise ValueError("A JSON request body is required.")
            try:
                return json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError("Request body must contain valid JSON.") from exc

        def _validated_body(self) -> dict[str, Any] | None:
            try:
                payload = self._body()
            except ValueError as exc:
                self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return None
            book, error = validate_book(payload)
            if error:
                self._send(HTTPStatus.BAD_REQUEST, {"error": error})
                return None
            return book

        def do_GET(self) -> None:
            status, response = handle_api("GET", self.path)
            self._send(status, response)

        def do_POST(self) -> None:
            try:
                payload = self._body()
            except ValueError as exc:
                self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            status, response = handle_api("POST", self.path, payload)
            self._send(status, response)

        def do_PUT(self) -> None:
            try:
                payload = self._body()
            except ValueError as exc:
                self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            status, response = handle_api("PUT", self.path, payload)
            self._send(status, response)

        def do_DELETE(self) -> None:
            status, response = handle_api("DELETE", self.path)
            self._send(status, response)

        def log_message(self, format: str, *args: Any) -> None:
            # Keep standard access logging, which is useful when run from a terminal.
            super().log_message(format, *args)

    BooksHandler.handle_api = staticmethod(handle_api)
    return BooksHandler


def serve(host: str = "127.0.0.1", port: int = 8000, database: str = DEFAULT_DATABASE) -> None:
    store = BookStore(database)
    server = ThreadingHTTPServer((host, port), make_handler(store))
    print(f"Books API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    serve(
        host=os.environ.get("BOOKS_HOST", "127.0.0.1"),
        port=int(os.environ.get("BOOKS_PORT", "8000")),
        database=DEFAULT_DATABASE,
    )
