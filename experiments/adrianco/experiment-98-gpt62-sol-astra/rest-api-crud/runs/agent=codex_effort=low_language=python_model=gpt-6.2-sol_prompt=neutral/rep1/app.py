"""SQLite-backed book collection WSGI application."""

import argparse
from contextlib import closing
from http import HTTPStatus
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

BOOK_PATH = re.compile(r"/books/([0-9]{1,19})")
MAX_BODY_BYTES = 64 * 1024


class APIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def read_book(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        raise APIError(400, "Invalid Content-Length.") from None
    if length < 0:
        raise APIError(400, "Invalid Content-Length.")
    if length > MAX_BODY_BYTES:
        raise APIError(413, "Request body is too large.")
    try:
        data = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
    except (ValueError, RecursionError):
        raise APIError(400, "Expected a JSON object.") from None
    if not isinstance(data, dict):
        raise APIError(400, "Expected a JSON object.")

    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise APIError(400, f"{field} must be a nonblank string.")

    year = data.get("year")
    if year is not None and (type(year) is not int or not -(2**63) <= year < 2**63):
        raise APIError(400, "year must be an integer in the SQLite integer range.")
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        raise APIError(400, "isbn must be a string.")

    fields = (data["title"].strip(), data["author"].strip(), year, isbn)
    try:
        for value in fields:
            if isinstance(value, str):
                value.encode("utf-8")
    except UnicodeEncodeError:
        raise APIError(400, "Book fields must contain valid Unicode.") from None
    return fields


def handle_books(db, environ, method, book_id):
    if book_id is None:
        if method == "POST":
            cursor = db.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                read_book(environ),
            )
            book_id = cursor.lastrowid
            book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return 201, dict(book), [("Location", f"/books/{book_id}")]

        filters = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        if "author" in filters:
            books = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id",
                (filters["author"][0],),
            )
        else:
            books = db.execute("SELECT * FROM books ORDER BY id")
        return 200, [dict(book) for book in books], []

    if method == "DELETE":
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            raise APIError(404, "Book not found.")
        return 204, None, []
    if method == "PUT":
        cursor = db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (*read_book(environ), book_id),
        )
        if cursor.rowcount == 0:
            raise APIError(404, "Book not found.")

    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        raise APIError(404, "Book not found.")
    return 200, dict(book), []


def create_app(database="books.sqlite3"):
    database = Path(database).resolve()
    with closing(sqlite3.connect(database)) as db, db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )"""
        )

    def application(environ, start_response):
        path = environ["PATH_INFO"]
        method = environ["REQUEST_METHOD"]
        match = BOOK_PATH.fullmatch(path)
        headers = []
        try:
            if path == "/health":
                allowed = "GET"
            elif path == "/books":
                allowed = "GET, POST"
            elif match and int(match[1]) < 2**63:
                allowed = "GET, PUT, DELETE"
            else:
                raise APIError(404, "Route not found.")

            if method not in allowed.split(", "):
                headers.append(("Allow", allowed))
                raise APIError(405, "Method not allowed.")
            if path == "/health":
                status, payload = 200, {"status": "ok"}
            else:
                with closing(sqlite3.connect(database)) as db, db:
                    db.row_factory = sqlite3.Row
                    status, payload, headers = handle_books(
                        db, environ, method, int(match[1]) if match else None
                    )
        except APIError as error:
            status, payload = error.status, {"error": str(error)}
        except sqlite3.Error:
            status, payload = 500, {"error": "Database operation failed."}

        body = b""
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers.extend([
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ])
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [body]

    return application


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="books.sqlite3")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    with make_server(args.host, args.port, create_app(args.database)) as server:
        print(f"Serving on http://{args.host}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
