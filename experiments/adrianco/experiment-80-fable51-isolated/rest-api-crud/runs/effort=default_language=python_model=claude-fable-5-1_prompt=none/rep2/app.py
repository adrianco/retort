"""Book collection REST API backed by SQLite.

Uses only the standard library (a WSGI app served by wsgiref), so it runs
without installing any third-party packages.
"""

import json
import os
import re
import sqlite3
from contextlib import closing
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
)
"""


def validate_book(data):
    """Return (clean_fields, errors) for a book payload."""
    if not isinstance(data, dict):
        return None, ["request body must be a JSON object"]

    errors = []
    clean = {}

    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} is required and must be a non-empty string")
        else:
            clean[field] = value.strip()

    year = data.get("year")
    # bool is a subclass of int, so reject it explicitly
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    clean["year"] = year

    isbn = data.get("isbn")
    if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
        errors.append("isbn must be a non-empty string")
    clean["isbn"] = isbn.strip() if isinstance(isbn, str) else None

    return clean, errors


BOOK_PATH = re.compile(r"/books/(\d+)")


def error(message, status, **extra):
    return status, {"error": message, **extra}, {}


def fetch_book(db, book_id):
    row = db.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return dict(row) if row else None


def read_json(environ):
    """Return the parsed JSON request body, or None if it is missing or malformed."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        return json.loads(environ["wsgi.input"].read(length))
    except ValueError:
        return None


def health(_db, _environ):
    return 200, {"status": "ok"}, {}


def create_book(db, environ):
    clean, errors = validate_book(read_json(environ))
    if errors:
        return error("validation failed", 400, details=errors)
    try:
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (clean["title"], clean["author"], clean["year"], clean["isbn"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("a book with this isbn already exists", 409)
    return 201, fetch_book(db, cur.lastrowid), {"Location": f"/books/{cur.lastrowid}"}


def list_books(db, environ):
    author = parse_qs(environ.get("QUERY_STRING", "")).get("author", [""])[0]
    query = "SELECT id, title, author, year, isbn FROM books"
    params = ()
    if author:
        query += " WHERE author = ? COLLATE NOCASE"
        params = (author,)
    rows = db.execute(query + " ORDER BY id", params).fetchall()
    return 200, [dict(row) for row in rows], {}


def get_book(db, _environ, book_id):
    book = fetch_book(db, book_id)
    if book is None:
        return error("book not found", 404)
    return 200, book, {}


def update_book(db, environ, book_id):
    if fetch_book(db, book_id) is None:
        return error("book not found", 404)
    clean, errors = validate_book(read_json(environ))
    if errors:
        return error("validation failed", 400, details=errors)
    try:
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (clean["title"], clean["author"], clean["year"], clean["isbn"], book_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("a book with this isbn already exists", 409)
    return 200, fetch_book(db, book_id), {}


def delete_book(db, _environ, book_id):
    cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    if cur.rowcount == 0:
        return error("book not found", 404)
    return 204, None, {}


def create_app(db_path=None):
    """Return a WSGI application storing books in the SQLite file at db_path."""
    db_path = db_path or os.environ.get("BOOKS_DB", "books.db")

    def connect():
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        return db

    with closing(connect()) as db:
        db.execute(SCHEMA)
        db.commit()

    def route(method, path):
        """Return (handlers_by_method, args) for a path, or None if unknown."""
        if path == "/health":
            return {"GET": health}, ()
        if path == "/books":
            return {"GET": list_books, "POST": create_book}, ()
        match = BOOK_PATH.fullmatch(path)
        if match:
            handlers = {"GET": get_book, "PUT": update_book, "DELETE": delete_book}
            return handlers, (int(match.group(1)),)
        return None

    def app(environ, start_response):
        method = environ["REQUEST_METHOD"]
        found = route(method, environ.get("PATH_INFO", ""))
        if found is None:
            status, body, headers = error("not found", 404)
        elif method not in found[0]:
            status, body, headers = error("method not allowed", 405)
            headers = {"Allow": ", ".join(sorted(found[0]))}
        else:
            handlers, args = found
            try:
                with closing(connect()) as db:
                    status, body, headers = handlers[method](db, environ, *args)
            except sqlite3.Error:
                status, body, headers = error("internal server error", 500)

        payload = b"" if body is None else json.dumps(body).encode("utf-8")
        if body is not None:
            headers = {**headers, "Content-Type": "application/json"}
        headers["Content-Length"] = str(len(payload))
        start_response(f"{status} {HTTPStatus(status).phrase}", list(headers.items()))
        return [payload]

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    with make_server("127.0.0.1", port, create_app()) as server:
        print(f"Listening on http://127.0.0.1:{port}")
        server.serve_forever()
