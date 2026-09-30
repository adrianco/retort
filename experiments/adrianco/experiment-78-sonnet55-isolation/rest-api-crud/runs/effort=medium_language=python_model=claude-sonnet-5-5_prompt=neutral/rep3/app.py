"""Book collection REST API (stdlib WSGI + SQLite)."""
import json
import os
import re
import sqlite3
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

FIELDS = ("title", "author", "year", "isbn")


class HTTPError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def init_db(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, author TEXT NOT NULL,
            year INTEGER, isbn TEXT)"""
    )
    conn.commit()


def validate(data):
    if not isinstance(data, dict):
        raise HTTPError(400, "body must be a JSON object")
    out = {}
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            raise HTTPError(400, f"{f} is required and must be a non-empty string")
        out[f] = v.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        raise HTTPError(400, "year must be an integer")
    out["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        raise HTTPError(400, "isbn must be a string")
    out["isbn"] = isbn
    return out


def row_to_dict(row):
    return {"id": row["id"], **{f: row[f] for f in FIELDS}}


def create_app(db_path=None):
    db_path = db_path or os.environ.get("BOOKS_DB", "books.db")
    if db_path == ":memory:":
        conn = sqlite3.connect(db_path, check_same_thread=False)
        connect = lambda: conn  # noqa: E731
    else:
        def connect():
            c = sqlite3.connect(db_path)
            return c
    c0 = connect()
    c0.row_factory = sqlite3.Row
    init_db(c0)

    def handle(method, path, query, body):
        if path == "/health" and method == "GET":
            return 200, {"status": "ok"}
        if path == "/books":
            if method == "POST":
                b = validate(body())
                cur = db.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                    (b["title"], b["author"], b["year"], b["isbn"]),
                )
                db.commit()
                return 201, {"id": cur.lastrowid, **b}
            if method == "GET":
                author = query.get("author", [None])[0]
                if author is not None:
                    rows = db.execute(
                        "SELECT * FROM books WHERE author = ? ORDER BY id", (author,))
                else:
                    rows = db.execute("SELECT * FROM books ORDER BY id")
                return 200, [row_to_dict(r) for r in rows]
            raise HTTPError(405, "method not allowed")
        m = re.fullmatch(r"/books/(\d+)", path)
        if m:
            bid = int(m.group(1))
            if method not in ("GET", "PUT", "DELETE"):
                raise HTTPError(405, "method not allowed")
            row = db.execute("SELECT * FROM books WHERE id = ?", (bid,)).fetchone()
            if row is None:
                raise HTTPError(404, "book not found")
            if method == "GET":
                return 200, row_to_dict(row)
            if method == "PUT":
                b = validate(body())
                db.execute(
                    "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                    (b["title"], b["author"], b["year"], b["isbn"], bid))
                db.commit()
                return 200, {"id": bid, **b}
            db.execute("DELETE FROM books WHERE id = ?", (bid,))
            db.commit()
            return 204, None
        raise HTTPError(404, "not found")

    STATUS = {200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request",
              404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"}

    def app(environ, start_response):
        nonlocal db
        db = connect()
        db.row_factory = sqlite3.Row

        def body():
            try:
                n = int(environ.get("CONTENT_LENGTH") or 0)
                return json.loads(environ["wsgi.input"].read(n) or b"")
            except (ValueError, UnicodeDecodeError):
                raise HTTPError(400, "invalid JSON body")

        try:
            status, payload = handle(
                environ["REQUEST_METHOD"], environ.get("PATH_INFO", "/").rstrip("/") or "/",
                parse_qs(environ.get("QUERY_STRING", "")), body)
        except HTTPError as e:
            status, payload = e.status, {"error": e.message}
        finally:
            if db_path != ":memory:":
                db.close()
        data = b"" if payload is None else json.dumps(payload).encode()
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(data)))]
        start_response(f"{status} {STATUS[status]}", headers)
        return [data]

    db = None
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Listening on http://127.0.0.1:{port}")
    make_server("127.0.0.1", port, create_app()).serve_forever()
