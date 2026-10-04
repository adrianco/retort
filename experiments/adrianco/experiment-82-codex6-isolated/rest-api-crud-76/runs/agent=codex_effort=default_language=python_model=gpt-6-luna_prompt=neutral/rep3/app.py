"""A small SQLite-backed REST API for a book collection.

Run with ``python app.py``. The application uses only the Python standard
library and exposes a WSGI callable named ``app``.
"""

import json
import os
import sqlite3
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


DATABASE = os.environ.get("BOOKS_DB_PATH", os.path.join(os.path.dirname(__file__), "books.db"))


def _connect():
    connection = sqlite3.connect(DATABASE)
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


def _response(start_response, status, payload=None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
    start_response(f"{status.value} {status.phrase}", headers)
    return [body]


def _read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        value = json.loads(environ["wsgi.input"].read(length) or b"{}")
    except (ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _validate(data):
    if not data or not isinstance(data.get("title"), str) or not data["title"].strip():
        return "title is required"
    if not isinstance(data.get("author"), str) or not data["author"].strip():
        return "author is required"
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        return "year must be an integer"
    for key in ("isbn",):
        if data.get(key) is not None and not isinstance(data[key], str):
            return f"{key} must be a string"
    return None


def app(environ, start_response):
    """WSGI application implementing the book collection endpoints."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/").rstrip("/") or "/"
    if path == "/health" and method == "GET":
        return _response(start_response, HTTPStatus.OK, {"status": "ok"})

    parts = path.strip("/").split("/")
    if parts[0] != "books" or len(parts) > 2:
        return _response(start_response, HTTPStatus.NOT_FOUND, {"error": "not found"})

    connection = _connect()
    try:
        if len(parts) == 1:
            if method == "GET":
                query = parse_qs(environ.get("QUERY_STRING", ""))
                author = query.get("author", [None])[0]
                rows = connection.execute(
                    "SELECT * FROM books WHERE (? IS NULL OR author = ?) ORDER BY id",
                    (author, author),
                ).fetchall()
                return _response(start_response, HTTPStatus.OK, [dict(row) for row in rows])
            if method == "POST":
                data = _read_json(environ)
                error = _validate(data)
                if error:
                    return _response(start_response, HTTPStatus.BAD_REQUEST, {"error": error})
                cursor = connection.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn")),
                )
                connection.commit()
                book = connection.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
                return _response(start_response, HTTPStatus.CREATED, dict(book))
            return _response(start_response, HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})

        try:
            book_id = int(parts[1])
            if book_id < 1:
                raise ValueError
        except ValueError:
            return _response(start_response, HTTPStatus.NOT_FOUND, {"error": "book not found"})
        existing = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if existing is None:
            return _response(start_response, HTTPStatus.NOT_FOUND, {"error": "book not found"})
        if method == "GET":
            return _response(start_response, HTTPStatus.OK, dict(existing))
        if method == "PUT":
            data = _read_json(environ)
            error = _validate(data)
            if error:
                return _response(start_response, HTTPStatus.BAD_REQUEST, {"error": error})
            connection.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn"), book_id),
            )
            connection.commit()
            updated = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return _response(start_response, HTTPStatus.OK, dict(updated))
        if method == "DELETE":
            connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
            connection.commit()
            return _response(start_response, HTTPStatus.NO_CONTENT)
        return _response(start_response, HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})
    finally:
        connection.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving book API on http://127.0.0.1:{port}")
    make_server("0.0.0.0", port, app).serve_forever()
