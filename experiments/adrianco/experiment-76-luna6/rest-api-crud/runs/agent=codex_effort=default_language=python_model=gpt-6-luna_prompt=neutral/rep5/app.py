"""A small WSGI JSON API for managing a book collection."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from http import HTTPStatus
from typing import Any, Callable
from urllib.parse import parse_qs


DEFAULT_DATABASE = os.environ.get("BOOKS_DATABASE", "books.db")
_BOOK_PATH = re.compile(r"^/books/(\d+)$")


def _connect(database: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )"""
    )
    return connection


def _book(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in ("id", "title", "author", "year", "isbn")}


def create_app(database: str = DEFAULT_DATABASE) -> Callable:
    """Return a WSGI application bound to *database*."""
    _connect(database).close()

    def respond(start_response: Callable, status: HTTPStatus, payload: Any = None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
        start_response(f"{status.value} {status.phrase}", headers)
        return [body]

    def application(environ: dict, start_response: Callable):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)

        def read_json() -> dict[str, Any] | None:
            try:
                length = int(environ.get("CONTENT_LENGTH") or "0")
                data = environ["wsgi.input"].read(length)
                value = json.loads(data or b"{}")
            except (ValueError, json.JSONDecodeError):
                return None
            return value if isinstance(value, dict) else None

        if path == "/health" and method == "GET":
            return respond(start_response, HTTPStatus.OK, {"status": "ok"})

        if path == "/books" and method == "GET":
            author = query.get("author", [None])[0]
            with _connect(database) as db:
                rows = db.execute("SELECT * FROM books WHERE (? IS NULL OR author = ?) ORDER BY id", (author, author)).fetchall()
            return respond(start_response, HTTPStatus.OK, [_book(row) for row in rows])

        if path == "/books" and method == "POST":
            payload = read_json()
            if payload is None:
                return respond(start_response, HTTPStatus.BAD_REQUEST, {"error": "Request body must be a JSON object"})
            title, author = payload.get("title"), payload.get("author")
            if not isinstance(title, str) or not title.strip() or not isinstance(author, str) or not author.strip():
                return respond(start_response, HTTPStatus.BAD_REQUEST, {"error": "title and author are required"})
            with _connect(database) as db:
                cursor = db.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                                    (title.strip(), author.strip(), payload.get("year"), payload.get("isbn")))
                row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return respond(start_response, HTTPStatus.CREATED, _book(row))

        match = _BOOK_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                with _connect(database) as db:
                    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                return respond(start_response, HTTPStatus.OK, _book(row)) if row else respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            if method == "PUT":
                payload = read_json()
                if payload is None:
                    return respond(start_response, HTTPStatus.BAD_REQUEST, {"error": "Request body must be a JSON object"})
                with _connect(database) as db:
                    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                    if row is None:
                        return respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
                    title, author = payload.get("title", row["title"]), payload.get("author", row["author"])
                    if not isinstance(title, str) or not title.strip() or not isinstance(author, str) or not author.strip():
                        return respond(start_response, HTTPStatus.BAD_REQUEST, {"error": "title and author are required"})
                    db.execute("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                               (title.strip(), author.strip(), payload.get("year", row["year"]), payload.get("isbn", row["isbn"]), book_id))
                    updated = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                return respond(start_response, HTTPStatus.OK, _book(updated))
            if method == "DELETE":
                with _connect(database) as db:
                    cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
                if cursor.rowcount == 0:
                    return respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
                return respond(start_response, HTTPStatus.NO_CONTENT)

        return respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Not found"})

    return application


app = create_app()


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    print("Serving book API at http://127.0.0.1:8000")
    make_server("127.0.0.1", 8000, app).serve_forever()
