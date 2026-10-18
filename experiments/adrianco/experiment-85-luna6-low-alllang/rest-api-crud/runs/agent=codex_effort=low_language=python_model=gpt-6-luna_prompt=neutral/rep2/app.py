"""A small SQLite-backed REST API for a personal book collection."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


DEFAULT_DATABASE = os.environ.get("BOOKS_DATABASE", "books.db")


class BookStore:
    """Persistence operations for books, using a SQLite database file."""

    def __init__(self, database: str = DEFAULT_DATABASE) -> None:
        self.database = database
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _book(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def create(self, book: dict[str, Any]) -> dict[str, Any]:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"].strip(), book["author"].strip(), book.get("year"), book.get("isbn")),
            )
            row = connection.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._book(row)

    def list(self, author: str | None = None) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection, connection:
            if author is None:
                rows = connection.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id", (author,)
                ).fetchall()
            return [self._book(row) for row in rows]

    def get(self, book_id: int) -> dict[str, Any] | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return self._book(row) if row else None

    def update(self, book_id: int, book: dict[str, Any]) -> dict[str, Any] | None:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"].strip(), book["author"].strip(), book.get("year"), book.get("isbn"), book_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return self._book(row)

    def delete(self, book_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0


def validate_book(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"
    title, author = payload.get("title"), payload.get("author")
    if not isinstance(title, str) or not title.strip():
        return None, "title is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return None, "author is required and must be a non-empty string"
    year = payload.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return None, "year must be an integer or null"
    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "isbn must be a string or null"
    return {"title": title, "author": author, "year": year, "isbn": isbn}, None


def make_handler(store: BookStore) -> type[BaseHTTPRequestHandler]:
    class BookHandler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: Any = None) -> None:
            data = b"" if body is None else json.dumps(body).encode("utf-8")
            self.send_response(status)
            if body is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)

        def _json_body(self) -> Any:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    raise ValueError
                return json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                raise ValueError("Request body must contain valid JSON") from None

        def _book_id(self, path: str) -> int | None:
            segment = path.removeprefix("/books/")
            if not segment or "/" in segment:
                return None
            try:
                value = int(segment)
                return value if value > 0 else None
            except ValueError:
                return None

        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send(HTTPStatus.OK, {"status": "ok"})
            elif parsed.path == "/books":
                author = parse_qs(parsed.query).get("author", [None])[0]
                self._send(HTTPStatus.OK, store.list(author))
            elif parsed.path.startswith("/books/"):
                book_id = self._book_id(parsed.path)
                if book_id is None:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": "Invalid book ID"})
                    return
                book = store.get(book_id)
                self._send(HTTPStatus.OK, book) if book else self._send(HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/books":
                self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            try:
                payload = self._json_body()
            except ValueError as error:
                self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            book, error = validate_book(payload)
            if error:
                self._send(HTTPStatus.BAD_REQUEST, {"error": error})
                return
            self._send(HTTPStatus.CREATED, store.create(book))

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            book_id = self._book_id(parsed.path) if parsed.path.startswith("/books/") else None
            if book_id is None:
                self._send(HTTPStatus.BAD_REQUEST, {"error": "Invalid book ID"})
                return
            try:
                payload = self._json_body()
            except ValueError as error:
                self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            book, error = validate_book(payload)
            if error:
                self._send(HTTPStatus.BAD_REQUEST, {"error": error})
                return
            updated = store.update(book_id, book)
            self._send(HTTPStatus.OK, updated) if updated else self._send(HTTPStatus.NOT_FOUND, {"error": "Book not found"})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            book_id = self._book_id(parsed.path) if parsed.path.startswith("/books/") else None
            if book_id is None:
                self._send(HTTPStatus.BAD_REQUEST, {"error": "Invalid book ID"})
                return
            if store.delete(book_id):
                self._send(HTTPStatus.NO_CONTENT)
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "Book not found"})

        def log_message(self, format: str, *args: Any) -> None:
            pass

    return BookHandler


def create_server(host: str = "127.0.0.1", port: int = 8000, database: str = DEFAULT_DATABASE) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(BookStore(database)))


if __name__ == "__main__":
    host = os.environ.get("BOOKS_HOST", "127.0.0.1")
    port = int(os.environ.get("BOOKS_PORT", "8000"))
    server = create_server(host, port)
    print(f"Book API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
