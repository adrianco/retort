"""Book collection REST API: stdlib WSGI app backed by SQLite."""
import json
import os
import re
import sqlite3
from wsgiref.simple_server import make_server

DB_PATH = os.environ.get("BOOKS_DB", "books.db")
BOOK_PATH = re.compile(r"^/books/(\d+)/?$")
FIELDS = ("title", "author", "year", "isbn")

STATUS = {200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request",
          404: "Not Found", 405: "Method Not Allowed"}


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
        "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
    )
    return conn


class ValidationError(Exception):
    pass


def validate(data):
    """Return a cleaned book dict or raise ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError("body must be a JSON object")
    errors = []
    clean = {}
    for name in ("title", "author"):
        v = data.get(name)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{name} is required and must be a non-empty string")
        else:
            clean[name] = v.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    clean["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    clean["isbn"] = isbn
    if errors:
        raise ValidationError("; ".join(errors))
    return clean


def create_app(db_path=None):
    db_path = db_path or DB_PATH
    conn = connect(db_path)

    def row(r):
        return {k: r[k] for k in ("id",) + FIELDS}

    def handle(method, path, query, body):
        if path == "/health":
            return (200, {"status": "ok"}) if method == "GET" else (405, {"error": "method not allowed"})
        if path.rstrip("/") == "/books":
            if method == "POST":
                data = validate(body())
                cur = conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                    (data["title"], data["author"], data["year"], data["isbn"]))
                conn.commit()
                data["id"] = cur.lastrowid
                return 201, row(data)
            if method == "GET":
                author = query.get("author")
                if author is not None:
                    rows = conn.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,))
                else:
                    rows = conn.execute("SELECT * FROM books ORDER BY id")
                return 200, [row(r) for r in rows]
            return 405, {"error": "method not allowed"}
        m = BOOK_PATH.match(path)
        if m:
            book_id = int(m.group(1))
            existing = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if method not in ("GET", "PUT", "DELETE"):
                return 405, {"error": "method not allowed"}
            if method == "PUT":
                data = validate(body())  # validate before existence check on body errors
            if existing is None:
                return 404, {"error": "book not found"}
            if method == "GET":
                return 200, row(existing)
            if method == "PUT":
                conn.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                             (data["title"], data["author"], data["year"], data["isbn"], book_id))
                conn.commit()
                data["id"] = book_id
                return 200, row(data)
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()
            return 204, None
        return 404, {"error": "not found"}

    def app(environ, start_response):
        def body():
            try:
                length = int(environ.get("CONTENT_LENGTH") or 0)
                raw = environ["wsgi.input"].read(length)
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise ValidationError("invalid JSON body")

        query = {}
        for part in environ.get("QUERY_STRING", "").split("&"):
            if "=" in part:
                from urllib.parse import unquote_plus
                k, v = part.split("=", 1)
                query[unquote_plus(k)] = unquote_plus(v)
        try:
            status, payload = handle(environ["REQUEST_METHOD"], environ["PATH_INFO"], query, body)
        except ValidationError as e:
            status, payload = 400, {"error": str(e)}
        data = b"" if payload is None else json.dumps(payload).encode()
        headers = [("Content-Length", str(len(data)))]
        if payload is not None:
            headers.append(("Content-Type", "application/json"))
        start_response(f"{status} {STATUS[status]}", headers)
        return [data]

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving on http://127.0.0.1:{port}")
    make_server("127.0.0.1", port, create_app()).serve_forever()
