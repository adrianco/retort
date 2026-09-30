"""Book collection REST API (stdlib only: WSGI + sqlite3)."""
import json
import os
import re
import sqlite3
from wsgiref.simple_server import make_server

FIELDS = ("title", "author", "year", "isbn")
BOOK_RE = re.compile(r"^/books/(\d+)/?$")


class HTTPError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL, author TEXT NOT NULL,"
        "year INTEGER, isbn TEXT)"
    )
    conn.commit()
    return conn


def validate(data):
    if not isinstance(data, dict):
        raise HTTPError(400, "JSON body must be an object")
    errors = []
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{f} is required and must be a non-empty string")
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    if errors:
        raise HTTPError(400, "; ".join(errors))
    return (data["title"].strip(), data["author"].strip(), year, isbn)


def create_app(db_path="books.db"):
    conn = connect(db_path)

    def get_book(book_id):
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise HTTPError(404, "book not found")
        return dict(row)

    def handle(method, path, query, body):
        if path == "/health" and method == "GET":
            return 200, {"status": "ok"}
        if path.rstrip("/") == "/books":
            if method == "POST":
                cur = conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                    validate(body()),
                )
                conn.commit()
                return 201, get_book(cur.lastrowid)
            if method == "GET":
                author = query.get("author")
                if author:
                    rows = conn.execute(
                        "SELECT * FROM books WHERE author = ? ORDER BY id", (author,))
                else:
                    rows = conn.execute("SELECT * FROM books ORDER BY id")
                return 200, [dict(r) for r in rows]
            raise HTTPError(405, "method not allowed")
        m = BOOK_RE.match(path)
        if m:
            book_id = int(m.group(1))
            if method == "GET":
                return 200, get_book(book_id)
            if method == "PUT":
                get_book(book_id)
                conn.execute(
                    "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                    validate(body()) + (book_id,),
                )
                conn.commit()
                return 200, get_book(book_id)
            if method == "DELETE":
                get_book(book_id)
                conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
                conn.commit()
                return 204, None
            raise HTTPError(405, "method not allowed")
        raise HTTPError(404, "not found")

    def app(environ, start_response):
        def body():
            try:
                n = int(environ.get("CONTENT_LENGTH") or 0)
                return json.loads(environ["wsgi.input"].read(n) or b"")
            except (ValueError, UnicodeDecodeError):
                raise HTTPError(400, "invalid JSON body")

        from urllib.parse import parse_qsl
        query = dict(parse_qsl(environ.get("QUERY_STRING", "")))
        try:
            status, payload = handle(
                environ["REQUEST_METHOD"], environ["PATH_INFO"], query, body)
        except HTTPError as e:
            status, payload = e.status, {"error": e.message}
        phrase = {200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request",
                  404: "Not Found", 405: "Method Not Allowed"}[status]
        data = b"" if payload is None else json.dumps(payload).encode()
        start_response(f"{status} {phrase}", [
            ("Content-Type", "application/json"), ("Content-Length", str(len(data)))])
        return [data]

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Listening on http://127.0.0.1:{port}")
    make_server("127.0.0.1", port, create_app(os.environ.get("DB_PATH", "books.db"))).serve_forever()
