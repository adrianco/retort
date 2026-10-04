"""A small SQLite-backed REST API for a book collection."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


DEFAULT_DATABASE = Path(__file__).with_name("books.db")
_BOOK_FIELDS = ("title", "author", "year", "isbn")


def _connect(database: str | os.PathLike[str]) -> sqlite3.Connection:
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
    return {"id": row["id"], **{field: row[field] for field in _BOOK_FIELDS}}


def _validate(payload: Any, *, partial: bool = False) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"
    if not partial:
        missing = [field for field in ("title", "author") if field not in payload]
        if missing:
            return None, f"Missing required field(s): {', '.join(missing)}"
    clean: dict[str, Any] = {}
    for field in _BOOK_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if field in ("title", "author"):
            if not isinstance(value, str) or not value.strip():
                return None, f"{field} must be a non-empty string"
            clean[field] = value.strip()
        elif field == "year":
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                return None, "year must be an integer or null"
            clean[field] = value
        else:
            if value is not None and not isinstance(value, str):
                return None, "isbn must be a string or null"
            clean[field] = value.strip() if isinstance(value, str) else None
    unknown = set(payload) - set(_BOOK_FIELDS)
    if unknown:
        return None, f"Unknown field(s): {', '.join(sorted(unknown))}"
    return clean, None


class BookAPI:
    """WSGI application. Pass a database path for isolated instances and tests."""

    def __init__(self, database: str | os.PathLike[str] = DEFAULT_DATABASE):
        self.database = str(database)
        with _connect(self.database):
            pass

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        try:
            if path == "/health" and method == "GET":
                return self._respond(start_response, HTTPStatus.OK, {"status": "ok"})
            if path == "/books":
                if method == "GET":
                    return self._list(start_response, query)
                if method == "POST":
                    return self._create(start_response, environ)
                return self._method_not_allowed(start_response, "GET, POST")
            match = re.fullmatch(r"/books/(\d+)", path)
            if match:
                book_id = int(match.group(1))
                if method == "GET":
                    return self._get(start_response, book_id)
                if method == "PUT":
                    return self._update(start_response, environ, book_id)
                if method == "DELETE":
                    return self._delete(start_response, book_id)
                return self._method_not_allowed(start_response, "GET, PUT, DELETE")
            return self._respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except (sqlite3.Error, OSError) as exc:
            return self._respond(start_response, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Database error"})

    def _read_json(self, environ: dict[str, Any]) -> tuple[Any, str | None]:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            if length <= 0:
                return None, "Request body is required"
            raw = environ["wsgi.input"].read(length)
            return json.loads(raw.decode("utf-8")), None
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None, "Request body must contain valid JSON"

    def _create(self, start_response: Callable[..., Any], environ: dict[str, Any]):
        payload, error = self._read_json(environ)
        clean, validation_error = _validate(payload) if error is None else (None, error)
        if validation_error:
            return self._respond(start_response, HTTPStatus.BAD_REQUEST, {"error": validation_error})
        with _connect(self.database) as db:
            cursor = db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (clean.get("title"), clean.get("author"), clean.get("year"), clean.get("isbn")),
            )
            created = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._respond(start_response, HTTPStatus.CREATED, _book(created), [("Location", f"/books/{created['id']}")])

    def _list(self, start_response: Callable[..., Any], query: dict[str, list[str]]):
        author = query.get("author", [None])[0]
        with _connect(self.database) as db:
            if author is None:
                rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
        return self._respond(start_response, HTTPStatus.OK, [_book(row) for row in rows])

    def _get(self, start_response: Callable[..., Any], book_id: int):
        with _connect(self.database) as db:
            row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return self._respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
        return self._respond(start_response, HTTPStatus.OK, _book(row))

    def _update(self, start_response: Callable[..., Any], environ: dict[str, Any], book_id: int):
        payload, error = self._read_json(environ)
        clean, validation_error = _validate(payload) if error is None else (None, error)
        if validation_error:
            return self._respond(start_response, HTTPStatus.BAD_REQUEST, {"error": validation_error})
        with _connect(self.database) as db:
            existing = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
            if existing is None:
                return self._respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            db.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (clean.get("title"), clean.get("author"), clean.get("year"), clean.get("isbn"), book_id),
            )
            row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._respond(start_response, HTTPStatus.OK, _book(row))

    def _delete(self, start_response: Callable[..., Any], book_id: int):
        with _connect(self.database) as db:
            cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            return self._respond(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
        return self._respond(start_response, HTTPStatus.NO_CONTENT, None)

    @staticmethod
    def _method_not_allowed(start_response: Callable[..., Any], allowed: str):
        return BookAPI._respond(start_response, HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Method not allowed"}, [("Allow", allowed)])

    @staticmethod
    def _respond(start_response: Callable[..., Any], status: HTTPStatus, data: Any, headers: list[tuple[str, str]] | None = None):
        body = b"" if data is None else json.dumps(data).encode("utf-8")
        response_headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
        if headers:
            response_headers.extend(headers)
        start_response(f"{status.value} {status.phrase}", response_headers)
        return [body]


app = BookAPI(os.environ.get("BOOKS_DATABASE", str(DEFAULT_DATABASE)))


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving book API on http://{host}:{port}")
    make_server(host, port, app).serve_forever()
