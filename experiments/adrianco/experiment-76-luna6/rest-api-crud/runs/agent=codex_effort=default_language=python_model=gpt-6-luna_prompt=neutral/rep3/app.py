"""Small JSON REST API for a SQLite-backed book collection."""

from __future__ import annotations

import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


DEFAULT_DATABASE = Path(__file__).with_name("books.db")


def initialize_database(database: str | Path = DEFAULT_DATABASE) -> None:
    """Create the books table if it does not exist."""
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )"""
        )


def _book_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in ("id", "title", "author", "year", "isbn")}


def make_handler(database: str | Path = DEFAULT_DATABASE) -> type[BaseHTTPRequestHandler]:
    """Bind a database path to an HTTP handler class (useful for isolated tests)."""

    class BookHandler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: Any) -> None:
            if status == 204:
                self.send_response(status)
                self.end_headers()
                return
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                value = json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError):
                raise ValueError("Request body must be valid JSON") from None
            if not isinstance(value, dict):
                raise ValueError("Request body must be a JSON object")
            return value

        def _connect(self) -> sqlite3.Connection:
            connection = sqlite3.connect(database)
            connection.row_factory = sqlite3.Row
            return connection

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send(200, {"status": "ok"})
                return
            if parsed.path == "/books":
                author = parse_qs(parsed.query).get("author", [None])[0]
                with self._connect() as connection:
                    if author is None:
                        rows = connection.execute("SELECT * FROM books ORDER BY id").fetchall()
                    else:
                        rows = connection.execute(
                            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                        ).fetchall()
                self._send(200, [_book_dict(row) for row in rows])
                return
            book_id = self._book_id(parsed.path)
            if book_id is None:
                self._send(404, {"error": "Not found"})
                return
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                self._send(404, {"error": "Book not found"})
            else:
                self._send(200, _book_dict(row))

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/books":
                self._send(404, {"error": "Not found"})
                return
            try:
                data = self._body()
                title, author, year, isbn = self._validate(data)
            except ValueError as error:
                self._send(400, {"error": str(error)})
                return
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    (title, author, year, isbn),
                )
                row = connection.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
            self._send(201, _book_dict(row))

        def do_PUT(self) -> None:
            book_id = self._book_id(urlparse(self.path).path)
            if book_id is None:
                self._send(404, {"error": "Not found"})
                return
            try:
                data = self._body()
                title, author, year, isbn = self._validate(data)
            except ValueError as error:
                self._send(400, {"error": str(error)})
                return
            with self._connect() as connection:
                cursor = connection.execute(
                    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                    (title, author, year, isbn, book_id),
                )
                row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if cursor.rowcount == 0:
                self._send(404, {"error": "Book not found"})
            else:
                self._send(200, _book_dict(row))

        def do_DELETE(self) -> None:
            book_id = self._book_id(urlparse(self.path).path)
            if book_id is None:
                self._send(404, {"error": "Not found"})
                return
            with self._connect() as connection:
                cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if cursor.rowcount == 0:
                self._send(404, {"error": "Book not found"})
            else:
                self._send(204, None)

        @staticmethod
        def _book_id(path: str) -> int | None:
            parts = path.strip("/").split("/")
            if len(parts) != 2 or parts[0] != "books":
                return None
            try:
                value = int(parts[1])
                return value if value > 0 else None
            except ValueError:
                return None

        @staticmethod
        def _validate(data: dict[str, Any]) -> tuple[str, str, int | None, str | None]:
            title = data.get("title")
            author = data.get("author")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("title is required and must be a non-empty string")
            if not isinstance(author, str) or not author.strip():
                raise ValueError("author is required and must be a non-empty string")
            year = data.get("year")
            if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
                raise ValueError("year must be an integer or null")
            isbn = data.get("isbn")
            if isbn is not None and not isinstance(isbn, str):
                raise ValueError("isbn must be a string or null")
            return title.strip(), author.strip(), year, isbn

        def log_message(self, format: str, *args: Any) -> None:
            # Keep request logs out of normal test and service output.
            return

    return BookHandler


def main() -> None:
    database = Path(os.environ.get("BOOKS_DATABASE", str(DEFAULT_DATABASE)))
    database.parent.mkdir(parents=True, exist_ok=True)
    initialize_database(database)
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), make_handler(database))
    print(f"Book API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
