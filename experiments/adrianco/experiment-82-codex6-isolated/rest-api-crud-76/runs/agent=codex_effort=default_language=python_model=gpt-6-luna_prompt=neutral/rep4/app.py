"""Small SQLite-backed REST API for a personal book collection."""

import json
import os
import sqlite3
from http import HTTPStatus
from urllib.parse import parse_qs


DATABASE = os.environ.get("BOOKS_DATABASE", "books.sqlite3")


def connect(database=DATABASE):
    db = sqlite3.connect(database)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    )""")
    return db


def response(start_response, status, body=None):
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"),
               ("Content-Length", str(len(payload)))]
    start_response(f"{status.value} {status.phrase}", headers)
    return [payload]


def book_dict(row):
    return dict(row)


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")
    if path == "/health" and method == "GET":
        return response(start_response, HTTPStatus.OK, {"status": "ok"})
    if path == "/books" and method == "GET":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        author = query.get("author", [None])[0]
        with connect() as db:
            rows = db.execute("SELECT * FROM books WHERE (? IS NULL OR author = ?) ORDER BY id",
                              (author, author)).fetchall()
        return response(start_response, HTTPStatus.OK, [book_dict(r) for r in rows])
    if path == "/books" and method == "POST":
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            data = json.loads(environ["wsgi.input"].read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, TypeError, json.JSONDecodeError):
            return response(start_response, HTTPStatus.BAD_REQUEST, {"error": "Request body must be a JSON object"})
        title, author = data.get("title"), data.get("author")
        if not isinstance(title, str) or not title.strip() or not isinstance(author, str) or not author.strip():
            return response(start_response, HTTPStatus.BAD_REQUEST, {"error": "title and author are required"})
        try:
            with connect() as db:
                cur = db.execute("INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)",
                                 (title.strip(), author.strip(), data.get("year"), data.get("isbn")))
                row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        except (sqlite3.Error, TypeError) as exc:
            return response(start_response, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return response(start_response, HTTPStatus.CREATED, book_dict(row))

    parts = path.strip("/").split("/")
    if len(parts) == 2 and parts[0] == "books":
        try:
            book_id = int(parts[1])
            if book_id <= 0:
                raise ValueError
        except ValueError:
            return response(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
        if method == "GET":
            with connect() as db:
                row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return response(start_response, HTTPStatus.OK, book_dict(row)) if row else response(
                start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
        if method == "PUT":
            try:
                length = int(environ.get("CONTENT_LENGTH") or 0)
                data = json.loads(environ["wsgi.input"].read(length) or b"{}")
                if not isinstance(data, dict):
                    raise ValueError
            except (ValueError, TypeError, json.JSONDecodeError):
                return response(start_response, HTTPStatus.BAD_REQUEST, {"error": "Request body must be a JSON object"})
            title, author = data.get("title"), data.get("author")
            if not isinstance(title, str) or not title.strip() or not isinstance(author, str) or not author.strip():
                return response(start_response, HTTPStatus.BAD_REQUEST, {"error": "title and author are required"})
            with connect() as db:
                cur = db.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                                 (title.strip(), author.strip(), data.get("year"), data.get("isbn"), book_id))
                row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
            if not cur.rowcount:
                return response(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            return response(start_response, HTTPStatus.OK, book_dict(row))
        if method == "DELETE":
            with connect() as db:
                cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if not cur.rowcount:
                return response(start_response, HTTPStatus.NOT_FOUND, {"error": "Book not found"})
            return response(start_response, HTTPStatus.NO_CONTENT)
    return response(start_response, HTTPStatus.NOT_FOUND, {"error": "Not found"})


application  # WSGI entry point

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    print("Serving book API on http://127.0.0.1:8000")
    make_server("127.0.0.1", 8000, application).serve_forever()
