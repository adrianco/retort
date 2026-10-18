"""A small SQLite-backed REST API for a book collection."""

import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


DEFAULT_DATABASE = os.path.join(os.path.dirname(__file__), "books.db")


def connect(database):
    db = sqlite3.connect(database)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS books (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               title TEXT NOT NULL,
               author TEXT NOT NULL,
               year INTEGER,
               isbn TEXT
           )"""
    )
    return db


def book_dict(row):
    return {key: row[key] for key in ("id", "title", "author", "year", "isbn")}


class BookAPI:
    """WSGI app that can be served by a standard-library HTTP server."""

    def __init__(self, database=DEFAULT_DATABASE):
        self.database = database

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        query = parse_qs(environ.get("QUERY_STRING", ""))
        status, payload = self.dispatch(method, path, query, self._body(environ))
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        phrase = {200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request", 404: "Not Found"}[status]
        start_response(f"{status} {phrase}", [("Content-Type", "application/json; charset=utf-8"),
                                                ("Content-Length", str(len(body)))])
        return [body]

    @staticmethod
    def _body(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
            data = json.loads(environ["wsgi.input"].read(length)) if length else None
            return data if isinstance(data, dict) else None
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def dispatch(self, method, path, query, data):
        if method == "GET" and path == "/health":
            return 200, {"status": "ok"}
        if method == "GET" and path == "/books":
            author = query.get("author", [None])[0]
            with connect(self.database) as db:
                rows = (db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
                        if author is not None else db.execute("SELECT * FROM books ORDER BY id").fetchall())
            return 200, [book_dict(row) for row in rows]
        if method == "POST" and path == "/books":
            return self.create(data)
        book_id = BookHandler.book_id(path)
        if book_id is None:
            return 404, {"error": "Not found"}
        if method == "GET":
            with connect(self.database) as db:
                row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return (404, {"error": "Book not found"}) if row is None else (200, book_dict(row))
        if method == "PUT":
            error = BookHandler.validate(data)
            if error:
                return 400, {"error": error}
            with connect(self.database) as db:
                cursor = db.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                                    (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn"), book_id))
                if cursor.rowcount == 0:
                    return 404, {"error": "Book not found"}
                row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
            return 200, book_dict(row)
        if method == "DELETE":
            with connect(self.database) as db:
                cursor = db.execute("DELETE FROM books WHERE id=?", (book_id,))
            return (204, None) if cursor.rowcount else (404, {"error": "Book not found"})
        return 404, {"error": "Not found"}

    def create(self, data):
        error = BookHandler.validate(data)
        if error:
            return 400, {"error": error}
        with connect(self.database) as db:
            cursor = db.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                                (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn")))
            row = db.execute("SELECT * FROM books WHERE id=?", (cursor.lastrowid,)).fetchone()
        return 201, book_dict(row)


class BookHandler(BaseHTTPRequestHandler):
    database = DEFAULT_DATABASE
    api = None

    def send_json(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def read_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self):
        self.dispatch_http("GET")

    def do_POST(self):
        self.dispatch_http("POST")

    def do_PUT(self):
        self.dispatch_http("PUT")

    def do_DELETE(self):
        self.dispatch_http("DELETE")

    def dispatch_http(self, method):
        parsed = urlparse(self.path)
        api = self.api or BookAPI(self.database)
        status, payload = api.dispatch(method, parsed.path, parse_qs(parsed.query), self.read_body())
        self.send_json(status, payload)

    @staticmethod
    def book_id(path):
        parts = path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "books":
            return None
        try:
            value = int(parts[1])
            return value if value > 0 else None
        except ValueError:
            return None

    @staticmethod
    def validate(data):
        if data is None:
            return "Request body must be a JSON object"
        for field in ("title", "author"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                return f"{field} is required"
        year = data.get("year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            return "year must be an integer or null"
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return "isbn must be a string or null"
        return None

    def log_message(self, *_args):
        pass


def serve(host="127.0.0.1", port=8000, database=DEFAULT_DATABASE):
    BookHandler.api = BookAPI(database)
    server = ThreadingHTTPServer((host, port), BookHandler)
    print(f"Book API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    serve(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")),
          database=os.environ.get("BOOKS_DATABASE", DEFAULT_DATABASE))
