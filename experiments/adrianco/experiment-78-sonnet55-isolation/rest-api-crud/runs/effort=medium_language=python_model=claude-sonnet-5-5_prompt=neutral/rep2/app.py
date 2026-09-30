"""Book collection REST API (stdlib WSGI + SQLite)."""
import json
import os
import re
import sqlite3
import threading
from wsgiref.simple_server import make_server, WSGIRequestHandler

STATUS = {200: "200 OK", 201: "201 Created", 204: "204 No Content",
          400: "400 Bad Request", 404: "404 Not Found",
          405: "405 Method Not Allowed", 409: "409 Conflict"}
FIELDS = ("title", "author", "year", "isbn")


class Store:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS books ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
            "author TEXT NOT NULL, year INTEGER, isbn TEXT)")
        self.conn.commit()


class ValidationError(Exception):
    pass


def validate(data):
    if not isinstance(data, dict):
        raise ValidationError("body must be a JSON object")
    out = {}
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            raise ValidationError(f"{f} is required and must be a non-empty string")
        out[f] = v.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        raise ValidationError("year must be an integer")
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        raise ValidationError("isbn must be a string")
    out["year"], out["isbn"] = year, isbn
    return out


def create_app(db_path=None):
    store = Store(db_path or os.environ.get("BOOKS_DB", "books.db"))
    route = re.compile(r"^/books/(\d+)$")

    def row(r):
        return {k: r[k] for k in ("id",) + FIELDS}

    def handle(method, path, query, body):
        if path == "/health":
            return (200, {"status": "ok"}) if method == "GET" else (405, {"error": "method not allowed"})
        c, lock = store.conn, store.lock
        if path == "/books":
            if method == "POST":
                b = validate(body())
                with lock:
                    cur = c.execute(
                        "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                        (b["title"], b["author"], b["year"], b["isbn"]))
                    c.commit()
                    r = c.execute("SELECT * FROM books WHERE id=?", (cur.lastrowid,)).fetchone()
                return 201, row(r)
            if method == "GET":
                author = query.get("author")
                with lock:
                    if author:
                        rows = c.execute("SELECT * FROM books WHERE author=? ORDER BY id", (author,))
                    else:
                        rows = c.execute("SELECT * FROM books ORDER BY id")
                    return 200, [row(r) for r in rows.fetchall()]
            return 405, {"error": "method not allowed"}
        m = route.match(path)
        if m:
            bid = int(m.group(1))
            if method not in ("GET", "PUT", "DELETE"):
                return 405, {"error": "method not allowed"}
            data = validate(body()) if method == "PUT" else None
            with lock:
                r = c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
                if r is None:
                    return 404, {"error": "book not found"}
                if method == "GET":
                    return 200, row(r)
                if method == "DELETE":
                    c.execute("DELETE FROM books WHERE id=?", (bid,))
                    c.commit()
                    return 204, None
                c.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                          (data["title"], data["author"], data["year"], data["isbn"], bid))
                c.commit()
                return 200, row(c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone())
        return 404, {"error": "not found"}

    def app(environ, start_response):
        from urllib.parse import parse_qs

        def body():
            try:
                n = int(environ.get("CONTENT_LENGTH") or 0)
                return json.loads(environ["wsgi.input"].read(n).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise ValidationError("invalid JSON body")

        query = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
        try:
            status, payload = handle(environ["REQUEST_METHOD"], environ["PATH_INFO"], query, body)
        except ValidationError as e:
            status, payload = 400, {"error": str(e)}
        data = b"" if payload is None else json.dumps(payload).encode()
        headers = [("Content-Length", str(len(data)))]
        if payload is not None:
            headers.append(("Content-Type", "application/json"))
        start_response(STATUS[status], headers)
        return [data]

    app.store = store
    return app


class _Quiet(WSGIRequestHandler):
    def log_message(self, *a):
        pass


def main():
    port = int(os.environ.get("PORT", "8000"))
    with make_server("0.0.0.0", port, create_app()) as srv:
        print(f"Serving on http://0.0.0.0:{port}")
        srv.serve_forever()


if __name__ == "__main__":
    main()
