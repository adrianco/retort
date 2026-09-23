"""A small SQLite-backed REST API for a personal book collection."""

import json
import os
import re
import sqlite3
from http import HTTPStatus
from wsgiref.simple_server import make_server


def create_app(database_path=None):
    """Return a WSGI application; pass a database path for persistent storage."""
    database_path = database_path or os.environ.get("BOOKS_DATABASE", "books.sqlite3")

    def connect():
        db = sqlite3.connect(database_path)
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )""")
        return db

    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        query = environ.get("QUERY_STRING", "")
        try:
            if path == "/health" and method == "GET":
                return respond(start_response, HTTPStatus.OK, {"status": "ok"})
            if path == "/books":
                if method == "GET":
                    from urllib.parse import parse_qs
                    author = parse_qs(query).get("author", [None])[0]
                    with connect() as db:
                        if author is None:
                            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
                        else:
                            rows = db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
                    return respond(start_response, HTTPStatus.OK, [dict(row) for row in rows])
                if method == "POST":
                    book = read_book(environ)
                    with connect() as db:
                        cursor = db.execute(
                            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                            (book["title"], book["author"], book["year"], book["isbn"]),
                        )
                        book["id"] = cursor.lastrowid
                    return respond(start_response, HTTPStatus.CREATED, book,
                                   [("Location", f"/books/{book['id']}")])
                return respond(start_response, HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"}, [("Allow", "GET, POST")])

            match = re.fullmatch(r"/books/(\d+)", path)
            if match:
                book_id = int(match.group(1))
                if method == "GET":
                    with connect() as db:
                        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                    return respond(start_response, HTTPStatus.OK, dict(row)) if row else not_found(start_response)
                if method == "PUT":
                    book = read_book(environ)
                    with connect() as db:
                        cursor = db.execute(
                            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                            (book["title"], book["author"], book["year"], book["isbn"], book_id),
                        )
                        if cursor.rowcount == 0:
                            return not_found(start_response)
                        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                    return respond(start_response, HTTPStatus.OK, dict(row))
                if method == "DELETE":
                    with connect() as db:
                        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
                    if cursor.rowcount == 0:
                        return not_found(start_response)
                    return respond(start_response, HTTPStatus.NO_CONTENT, None)
                return respond(start_response, HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"}, [("Allow", "GET, PUT, DELETE")])
            return respond(start_response, HTTPStatus.NOT_FOUND, {"error": "not found"})
        except (ValueError, json.JSONDecodeError) as exc:
            return respond(start_response, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except sqlite3.Error:
            return respond(start_response, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "database error"})

    return application


def read_book(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        payload = environ["wsgi.input"].read(length)
        data = json.loads(payload or b"{}")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("request body must be valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("request body must be a JSON object")
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
    return {"title": title.strip(), "author": author.strip(), "year": year, "isbn": isbn}


def respond(start_response, status, value, headers=()):
    body = b"" if value is None else json.dumps(value).encode("utf-8")
    response_headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
    response_headers.extend(headers)
    start_response(f"{status.value} {status.phrase}", response_headers)
    return [body]


def not_found(start_response):
    return respond(start_response, HTTPStatus.NOT_FOUND, {"error": "book not found"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving book API on http://127.0.0.1:{port}")
    make_server("0.0.0.0", port, create_app()).serve_forever()
