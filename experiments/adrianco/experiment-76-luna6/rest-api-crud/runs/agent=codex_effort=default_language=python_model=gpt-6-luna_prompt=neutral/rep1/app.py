"""Small SQLite-backed REST API for a personal book collection."""

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


def _connect(db_path):
    connection = sqlite3.connect(db_path)
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


@contextmanager
def _database(db_path):
    connection = _connect(db_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _validated_book(data):
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    title, author = data.get("title"), data.get("author")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title is required")
    if not isinstance(author, str) or not author.strip():
        raise ValueError("author is required")
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        raise ValueError("year must be an integer or null")
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        raise ValueError("isbn must be a string or null")
    return title.strip(), author.strip(), year, isbn


def create_app(db_path=None):
    """Return a WSGI application; db_path is injectable for tests."""
    db_path = db_path or os.environ.get("BOOKS_DB", "books.sqlite3")

    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        query = parse_qs(environ.get("QUERY_STRING", ""))
        status, payload = HTTPStatus.OK, None

        def body():
            try:
                length = int(environ.get("CONTENT_LENGTH") or "0")
                raw = environ["wsgi.input"].read(length)
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("Request body must contain valid JSON")

        try:
            with _database(db_path) as db:
                if path == "/health" and method == "GET":
                    payload = {"status": "ok"}
                elif path == "/books" and method == "GET":
                    author = query.get("author", [None])[0]
                    if author is None:
                        rows = db.execute("SELECT * FROM books ORDER BY id")
                    else:
                        rows = db.execute(
                            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                        )
                    payload = [dict(row) for row in rows]
                elif path == "/books" and method == "POST":
                    values = _validated_book(body())
                    cursor = db.execute(
                        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                        values,
                    )
                    payload = dict(db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone())
                    status = HTTPStatus.CREATED
                else:
                    match = re.fullmatch(r"/books/(\d+)", path)
                    if not match:
                        status, payload = HTTPStatus.NOT_FOUND, {"error": "Not found"}
                    else:
                        book_id = int(match.group(1))
                        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                        if method == "GET":
                            if row is None:
                                status, payload = HTTPStatus.NOT_FOUND, {"error": "Book not found"}
                            else:
                                payload = dict(row)
                        elif method == "PUT":
                            values = _validated_book(body())
                            if row is None:
                                status, payload = HTTPStatus.NOT_FOUND, {"error": "Book not found"}
                            else:
                                db.execute(
                                    "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                                    (*values, book_id),
                                )
                                payload = dict(db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone())
                        elif method == "DELETE":
                            if row is None:
                                status, payload = HTTPStatus.NOT_FOUND, {"error": "Book not found"}
                            else:
                                db.execute("DELETE FROM books WHERE id=?", (book_id,))
                                status, payload = HTTPStatus.NO_CONTENT, None
                        else:
                            status, payload = HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Method not allowed"}
        except ValueError as exc:
            status, payload = HTTPStatus.BAD_REQUEST, {"error": str(exc)}

        response = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(response)))]
        if status == HTTPStatus.METHOD_NOT_ALLOWED:
            headers.append(("Allow", "GET, POST, PUT, DELETE"))
        start_response(f"{status.value} {status.phrase}", headers)
        return [response]

    return app


def main():
    port = int(os.environ.get("PORT", "8000"))
    with make_server("0.0.0.0", port, create_app()) as server:
        print(f"Serving book API on http://127.0.0.1:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
