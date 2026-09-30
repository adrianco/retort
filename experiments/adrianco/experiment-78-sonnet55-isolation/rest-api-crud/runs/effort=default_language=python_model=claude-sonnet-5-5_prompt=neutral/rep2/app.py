"""Book collection REST API (stdlib only: WSGI + sqlite3)."""
import json
import os
import re
import sqlite3
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

DB_PATH = os.environ.get("BOOKS_DB", "books.db")
FIELDS = ("title", "author", "year", "isbn")


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
        "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
    )
    conn.commit()
    return conn


def validate(data):
    """Return (clean, errors) for a book payload."""
    if not isinstance(data, dict):
        return None, ["body must be a JSON object"]
    errors = []
    clean = {}
    for f in ("title", "author"):
        v = data.get(f)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{f} is required and must be a non-empty string")
        else:
            clean[f] = v.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")
    clean["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")
    clean["isbn"] = isbn
    return clean, errors


class App:
    def __init__(self, db_path=None):
        self.db = connect(db_path or DB_PATH)

    def __call__(self, environ, start_response):
        try:
            status, body = self.dispatch(environ)
        except Exception:  # pragma: no cover
            status, body = 500, {"error": "internal server error"}
        payload = json.dumps(body).encode()
        start_response(
            f"{status} {'OK' if status < 400 else 'Error'}",
            [("Content-Type", "application/json"),
             ("Content-Length", str(len(payload)))],
        )
        return [payload]

    def dispatch(self, environ):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "").rstrip("/") or "/"
        if path == "/health":
            return (200, {"status": "ok"}) if method == "GET" else (405, {"error": "method not allowed"})
        if path == "/books":
            if method == "POST":
                return self.create(environ)
            if method == "GET":
                return self.list(environ)
            return 405, {"error": "method not allowed"}
        m = re.fullmatch(r"/books/(\d+)", path)
        if m:
            book_id = int(m.group(1))
            if method == "GET":
                return self.get(book_id)
            if method == "PUT":
                return self.update(book_id, environ)
            if method == "DELETE":
                return self.delete(book_id)
            return 405, {"error": "method not allowed"}
        return 404, {"error": "not found"}

    @staticmethod
    def read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            return json.loads(environ["wsgi.input"].read(length) or b"null"), None
        except (ValueError, UnicodeDecodeError):
            return None, "invalid JSON"

    def row(self, book_id):
        r = self.db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(r) if r else None

    def create(self, environ):
        data, err = self.read_json(environ)
        if err:
            return 400, {"error": err}
        clean, errors = validate(data)
        if errors:
            return 400, {"error": "validation failed", "details": errors}
        cur = self.db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
            tuple(clean[f] for f in FIELDS),
        )
        self.db.commit()
        return 201, self.row(cur.lastrowid)

    def list(self, environ):
        qs = parse_qs(environ.get("QUERY_STRING", ""))
        if "author" in qs:
            rows = self.db.execute(
                "SELECT * FROM books WHERE author=? ORDER BY id", (qs["author"][0],))
        else:
            rows = self.db.execute("SELECT * FROM books ORDER BY id")
        return 200, [dict(r) for r in rows]

    def get(self, book_id):
        book = self.row(book_id)
        return (200, book) if book else (404, {"error": "book not found"})

    def update(self, book_id, environ):
        if not self.row(book_id):
            return 404, {"error": "book not found"}
        data, err = self.read_json(environ)
        if err:
            return 400, {"error": err}
        clean, errors = validate(data)
        if errors:
            return 400, {"error": "validation failed", "details": errors}
        self.db.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (*(clean[f] for f in FIELDS), book_id),
        )
        self.db.commit()
        return 200, self.row(book_id)

    def delete(self, book_id):
        cur = self.db.execute("DELETE FROM books WHERE id=?", (book_id,))
        self.db.commit()
        if cur.rowcount == 0:
            return 404, {"error": "book not found"}
        return 200, {"deleted": book_id}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Listening on http://127.0.0.1:{port}")
    make_server("127.0.0.1", port, App()).serve_forever()
