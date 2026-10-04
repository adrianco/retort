"""A small JSON REST API for a SQLite-backed book collection."""

import json
import os
import re
import sqlite3
from http import HTTPStatus
from wsgiref.simple_server import make_server


class BookStore:
    def __init__(self, database_path):
        self.database_path = database_path
        with self.connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )"""
            )

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


class BooksAPI:
    def __init__(self, database_path=None):
        self.store = BookStore(database_path or os.environ.get("BOOKS_DB", "books.db"))

    @staticmethod
    def response(start_response, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
        start_response(f"{status.value} {status.phrase}", headers)
        return [body]

    @staticmethod
    def read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            if length <= 0:
                raise ValueError("Request body must be a JSON object")
            data = json.loads(environ["wsgi.input"].read(length))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Request body must be valid JSON")
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    @staticmethod
    def validate(data):
        if not isinstance(data.get("title"), str) or not data["title"].strip():
            raise ValueError("title is required and must be a non-empty string")
        if not isinstance(data.get("author"), str) or not data["author"].strip():
            raise ValueError("author is required and must be a non-empty string")
        year = data.get("year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            raise ValueError("year must be an integer or null")
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            raise ValueError("isbn must be a string or null")
        return {"title": data["title"].strip(), "author": data["author"].strip(), "year": year, "isbn": isbn}

    @staticmethod
    def book(row):
        return dict(row)

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")
        if method == "GET" and path == "/health":
            return self.response(start_response, HTTPStatus.OK, {"status": "ok"})

        match = re.fullmatch(r"/books(?:/(\d+))?/?", path)
        if not match:
            return self.response(start_response, HTTPStatus.NOT_FOUND, {"error": "Not found"})
        book_id = int(match.group(1)) if match.group(1) else None

        try:
            if book_id is None and method == "POST":
                data = self.validate(self.read_json(environ))
                with self.store.connect() as db:
                    cursor = db.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", tuple(data.values()))
                    row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
                return self.response(start_response, HTTPStatus.CREATED, self.book(row))

            if book_id is None and method == "GET":
                author = environ.get("QUERY_STRING", "")
                from urllib.parse import parse_qs
                filters = parse_qs(author)
                author_filter = filters.get("author", [None])[0]
                with self.store.connect() as db:
                    rows = db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author_filter,)).fetchall() if author_filter is not None else db.execute("SELECT * FROM books ORDER BY id").fetchall()
                return self.response(start_response, HTTPStatus.OK, [self.book(row) for row in rows])

            if book_id is not None and method == "GET":
                with self.store.connect() as db:
                    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                return self.response(start_response, HTTPStatus.OK, self.book(row)) if row else self.response(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})

            if book_id is not None and method == "PUT":
                data = self.validate(self.read_json(environ))
                with self.store.connect() as db:
                    cursor = db.execute("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", (*data.values(), book_id))
                    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone() if cursor.rowcount else None
                return self.response(start_response, HTTPStatus.OK, self.book(row)) if row else self.response(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})

            if book_id is not None and method == "DELETE":
                with self.store.connect() as db:
                    cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
                return self.response(start_response, HTTPStatus.NO_CONTENT) if cursor.rowcount else self.response(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})

            allowed = method in ("GET", "POST") if book_id is None else method in ("GET", "PUT", "DELETE")
            return self.response(start_response, HTTPStatus.METHOD_NOT_ALLOWED if allowed is False else HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Method not allowed"})
        except ValueError as error:
            return self.response(start_response, HTTPStatus.BAD_REQUEST, {"error": str(error)})


app = BooksAPI()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    with make_server("0.0.0.0", port, app) as server:
        print(f"Books API listening on http://0.0.0.0:{port}")
        server.serve_forever()
