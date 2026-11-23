"""SQLite-backed book collection WSGI application."""
import json
import os
import re
import sqlite3
from contextlib import closing
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


def read_book(env):
    if env.get("CONTENT_TYPE", "").partition(";")[0].strip().lower() != "application/json":
        return 415, {"error": "Use application/json"}
    try:
        size = int(env.get("CONTENT_LENGTH") or 0)
        if not 0 < size <= 1_000_000:
            raise ValueError
        book = json.loads(env["wsgi.input"].read(size).decode("utf-8"))
    except (ValueError, RecursionError):
        return 400, {"error": "Expected a UTF-8 JSON body up to 1 MB"}
    if not isinstance(book, dict):
        return 400, {"error": "Expected a book object"}
    for key in ("title", "author"):
        if not isinstance(book.get(key), str) or not book[key].strip():
            return 400, {"error": f"{key} must be a nonempty string"}
        book[key] = book[key].strip()
    year = book.get("year")
    if year is not None and (type(year) is not int or not -(2**63) <= year < 2**63):
        return 400, {"error": "year must be a 64-bit integer or null"}
    if book.get("isbn") is not None and not isinstance(book["isbn"], str):
        return 400, {"error": "isbn must be a string or null"}
    try:
        for key in ("title", "author", "isbn"):
            (book.get(key) or "").encode("utf-8")
    except UnicodeEncodeError:
        return 400, {"error": "Invalid Unicode in book"}
    return 200, book


def create_app(path="books.sqlite3"):
    def connect():
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        return db

    with closing(connect()) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            author TEXT NOT NULL, year INTEGER, isbn TEXT)""")

    def route(env, headers):
        path = env["PATH_INFO"]
        method = env["REQUEST_METHOD"]
        match = re.fullmatch(r"/books/([0-9]+)", path)
        if path == "/health":
            allowed = ("GET",)
        elif path == "/books":
            allowed = ("GET", "POST")
        elif match:
            allowed = ("GET", "PUT", "DELETE")
        else:
            return 404, {"error": "Route not found"}
        if method not in allowed:
            headers.append(("Allow", ", ".join(allowed)))
            return 405, {"error": "Method not allowed"}
        with closing(connect()) as db, db:
            if path == "/health":
                db.execute("SELECT id FROM books LIMIT 1").fetchone()
                return 200, {"status": "ok"}
            book_id = match[1] if match else None
            if method == "GET" and not match:
                query = parse_qs(env.get("QUERY_STRING", ""), keep_blank_values=True)
                if "author" in query:
                    rows = db.execute("SELECT * FROM books WHERE author=? ORDER BY id",
                                      (query["author"][0],))
                else:
                    rows = db.execute("SELECT * FROM books ORDER BY id")
                return 200, [dict(row) for row in rows]
            if method in ("POST", "PUT"):
                status, book = read_book(env)
                if status != 200:
                    return status, book
                values = tuple(book.get(k) for k in ("title", "author", "year", "isbn"))
                if method == "POST":
                    book_id = db.execute(
                        "INSERT INTO books(title,author,year,isbn) VALUES (?,?,?,?)", values
                    ).lastrowid
                    headers.append(("Location", f"/books/{book_id}"))
                else:
                    db.execute("UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?",
                               (*values, book_id))
            if method == "DELETE":
                if db.execute("DELETE FROM books WHERE id=?", (book_id,)).rowcount:
                    return 200, {"id": int(book_id), "deleted": True}
            else:
                row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
                if row:
                    return (201 if method == "POST" else 200), dict(row)
            return 404, {"error": "Book not found"}

    def application(env, start_response):
        headers = []
        try:
            status, data = route(env, headers)
        except sqlite3.Error:
            status, data, headers = 503, {"error": "Database unavailable"}, []
        body = json.dumps(data).encode()
        headers.extend([("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [body]

    return application


if __name__ == "__main__":
    with make_server("127.0.0.1", int(os.getenv("PORT", "8000")),
                     create_app(os.getenv("BOOKS_DB", "books.sqlite3"))) as server:
        server.serve_forever()
