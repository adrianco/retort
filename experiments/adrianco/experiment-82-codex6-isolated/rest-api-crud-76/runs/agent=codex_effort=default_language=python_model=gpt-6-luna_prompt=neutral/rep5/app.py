"""A small JSON REST API for a SQLite-backed book collection."""
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


DEFAULT_DB = os.environ.get("BOOKS_DB", "books.db")


def connect(db_path):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    )""")
    return db


def create_handler(db_path=DEFAULT_DB):
    class BooksHandler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def body_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("JSON body must be an object")
                return data
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                raise ValueError("Request body must be a valid JSON object")

        @staticmethod
        def normalize(data):
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
            return (title.strip(), author.strip(), year, isbn)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self.send_json(200, {"status": "ok"})
                return
            if parsed.path == "/books":
                author = parse_qs(parsed.query).get("author", [None])[0]
                with connect(db_path) as db:
                    if author is None:
                        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
                    else:
                        rows = db.execute("SELECT * FROM books WHERE author LIKE ? COLLATE NOCASE ORDER BY id", ("%" + author + "%",)).fetchall()
                self.send_json(200, [dict(row) for row in rows])
                return
            book_id = self.book_id(parsed.path)
            if book_id is not None:
                with connect(db_path) as db:
                    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                if row is None:
                    self.send_json(404, {"error": "Book not found"})
                else:
                    self.send_json(200, dict(row))
                return
            self.send_json(404, {"error": "Not found"})

        def do_POST(self):
            if urlparse(self.path).path != "/books":
                self.send_json(404, {"error": "Not found"})
                return
            try:
                values = self.normalize(self.body_json())
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
                return
            with connect(db_path) as db:
                cursor = db.execute("INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)", values)
                row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
            self.send_json(201, dict(row))

        def do_PUT(self):
            book_id = self.book_id(urlparse(self.path).path)
            if book_id is None:
                self.send_json(404, {"error": "Not found"})
                return
            try:
                values = self.normalize(self.body_json())
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
                return
            with connect(db_path) as db:
                cursor = db.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?", (*values, book_id))
                row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if cursor.rowcount == 0:
                self.send_json(404, {"error": "Book not found"})
            else:
                self.send_json(200, dict(row))

        def do_DELETE(self):
            book_id = self.book_id(urlparse(self.path).path)
            if book_id is None:
                self.send_json(404, {"error": "Not found"})
                return
            with connect(db_path) as db:
                cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if cursor.rowcount == 0:
                self.send_json(404, {"error": "Book not found"})
            else:
                self.send_json(204, None)

        @staticmethod
        def book_id(path):
            parts = path.strip("/").split("/")
            if len(parts) == 2 and parts[0] == "books" and parts[1].isdigit():
                return int(parts[1])
            return None

        def log_message(self, fmt, *args):
            pass

    return BooksHandler


def serve(host="127.0.0.1", port=8000, db_path=DEFAULT_DB):
    server = ThreadingHTTPServer((host, port), create_handler(db_path))
    print(f"Book API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    serve(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")))
