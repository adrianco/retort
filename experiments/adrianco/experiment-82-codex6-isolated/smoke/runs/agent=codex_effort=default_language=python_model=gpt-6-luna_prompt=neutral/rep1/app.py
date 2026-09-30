"""A small JSON REST API for a SQLite-backed book collection."""

import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


DB_PATH = os.environ.get("BOOKS_DB", os.path.join(os.path.dirname(__file__), "books.db"))


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS books (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               title TEXT NOT NULL,
               author TEXT NOT NULL,
               year INTEGER,
               isbn TEXT
           )"""
    )
    return connection


class BookHandler(BaseHTTPRequestHandler):
    def send_json(self, status, value):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_book_payload(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None, "Request body must be valid JSON"
        if not isinstance(payload, dict):
            return None, "Request body must be a JSON object"
        title, author = payload.get("title"), payload.get("author")
        if not isinstance(title, str) or not title.strip():
            return None, "title is required"
        if not isinstance(author, str) or not author.strip():
            return None, "author is required"
        year = payload.get("year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            return None, "year must be an integer or null"
        isbn = payload.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return None, "isbn must be a string or null"
        return {"title": title.strip(), "author": author.strip(), "year": year, "isbn": isbn}, None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self.send_json(200, {"status": "ok"})
        if parsed.path == "/books":
            author = parse_qs(parsed.query).get("author", [None])[0]
            with connect_db() as db:
                if author is None:
                    rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
                else:
                    rows = db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
            return self.send_json(200, [dict(row) for row in rows])
        book_id = self.book_id(parsed.path)
        if book_id is not None:
            with connect_db() as db:
                row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                return self.send_json(404, {"error": "Book not found"})
            return self.send_json(200, dict(row))
        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/books":
            return self.send_json(404, {"error": "Not found"})
        book, error = self.read_book_payload()
        if error:
            return self.send_json(400, {"error": error})
        with connect_db() as db:
            cursor = db.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                                (book["title"], book["author"], book["year"], book["isbn"]))
            row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        self.send_json(201, dict(row))

    def do_PUT(self):
        book_id = self.book_id(urlparse(self.path).path)
        if book_id is None:
            return self.send_json(404, {"error": "Not found"})
        book, error = self.read_book_payload()
        if error:
            return self.send_json(400, {"error": error})
        with connect_db() as db:
            cursor = db.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                                (book["title"], book["author"], book["year"], book["isbn"], book_id))
            row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return self.send_json(404, {"error": "Book not found"})
        self.send_json(200, dict(row))

    def do_DELETE(self):
        book_id = self.book_id(urlparse(self.path).path)
        if book_id is None:
            return self.send_json(404, {"error": "Not found"})
        with connect_db() as db:
            cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            return self.send_json(404, {"error": "Book not found"})
        self.send_json(200, {"deleted": True})

    @staticmethod
    def book_id(path):
        pieces = path.strip("/").split("/")
        if len(pieces) != 2 or pieces[0] != "books":
            return None
        try:
            value = int(pieces[1])
            return value if value > 0 else None
        except ValueError:
            return None

    def log_message(self, fmt, *args):
        # Keep the default server quiet; deployments can add structured logging.
        pass


def serve(host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), BookHandler)
    print(f"Book API listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    serve(os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000")))
