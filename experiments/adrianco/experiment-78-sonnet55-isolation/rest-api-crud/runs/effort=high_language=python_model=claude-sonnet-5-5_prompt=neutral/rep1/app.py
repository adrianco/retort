"""Book collection REST API: stdlib WSGI app backed by SQLite (no third-party deps)."""
import json
import os
import re
import sqlite3
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

DEFAULT_DB = os.environ.get("BOOKS_DB", "books.db")
BOOK_ROUTE = re.compile(r"^/books/([^/]+)/?$")
MAX_BODY = 1_000_000

STATUS_TEXT = {
    200: "200 OK",
    201: "201 Created",
    400: "400 Bad Request",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    413: "413 Payload Too Large",
    422: "422 Unprocessable Entity",
    500: "500 Internal Server Error",
}


class HTTPError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def init_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS books (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   author TEXT NOT NULL,
                   year INTEGER,
                   isbn TEXT
               )"""
        )
    conn.close()


def validate_book(data):
    """Return a cleaned dict of book fields, or raise HTTPError(422)."""
    if not isinstance(data, dict):
        raise HTTPError(400, "Request body must be a JSON object")
    errors = {}
    clean = {}
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            clean[field] = value.strip()
    year = data.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    else:
        clean["year"] = year
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    else:
        clean["isbn"] = isbn
    if errors:
        raise HTTPError(422, "Validation failed", errors)
    return clean


def row_to_dict(row):
    return {k: row[k] for k in row.keys()}


class BookApp:
    def __init__(self, db_path=DEFAULT_DB):
        self.db_path = db_path
        init_db(db_path)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- WSGI entry point -------------------------------------------------
    def __call__(self, environ, start_response):
        try:
            status, payload = self.dispatch(environ)
        except HTTPError as exc:
            status = exc.status
            payload = {"error": exc.message}
            if exc.details:
                payload["details"] = exc.details
        except Exception:  # pragma: no cover - defensive
            status, payload = 500, {"error": "Internal server error"}
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ]
        start_response(STATUS_TEXT[status], headers)
        return [body]

    # --- routing ----------------------------------------------------------
    def dispatch(self, environ):
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO", "") or "/"

        if path == "/health":
            self._allow(method, ("GET",))
            return 200, {"status": "ok"}
        if path.rstrip("/") == "/books":
            self._allow(method, ("GET", "POST"))
            if method == "POST":
                return self.create_book(self._read_json(environ))
            return self.list_books(environ.get("QUERY_STRING", ""))
        match = BOOK_ROUTE.match(path)
        if match:
            self._allow(method, ("GET", "PUT", "DELETE"))
            book_id = self._parse_id(match.group(1))
            if method == "GET":
                return self.get_book(book_id)
            if method == "PUT":
                return self.update_book(book_id, self._read_json(environ))
            return self.delete_book(book_id)
        raise HTTPError(404, "Not found")

    @staticmethod
    def _allow(method, allowed):
        if method not in allowed:
            raise HTTPError(405, "Method not allowed")

    @staticmethod
    def _parse_id(raw):
        if not raw.isascii() or not raw.isdigit():
            raise HTTPError(404, "Book not found")
        return int(raw)

    @staticmethod
    def _read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HTTPError(400, "Invalid Content-Length")
        if length > MAX_BODY:
            raise HTTPError(413, "Request body too large")
        raw = environ["wsgi.input"].read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, "Request body must be valid JSON")

    # --- handlers ---------------------------------------------------------
    def create_book(self, data):
        book = validate_book(data)
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    (book["title"], book["author"], book["year"], book["isbn"]),
                )
            return 201, {"id": cur.lastrowid, **book}
        finally:
            conn.close()

    def list_books(self, query_string):
        from urllib.parse import parse_qs

        author = parse_qs(query_string).get("author", [None])[0]
        sql, params = "SELECT * FROM books", ()
        if author is not None:
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        conn = self._connect()
        try:
            rows = conn.execute(sql + " ORDER BY id", params).fetchall()
            return 200, [row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get_book(self, book_id):
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPError(404, "Book not found")
        return 200, row_to_dict(row)

    def update_book(self, book_id, data):
        book = validate_book(data)
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                    (book["title"], book["author"], book["year"], book["isbn"], book_id),
                )
            if cur.rowcount == 0:
                raise HTTPError(404, "Book not found")
            return 200, {"id": book_id, **book}
        finally:
            conn.close()

    def delete_book(self, book_id):
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if cur.rowcount == 0:
                raise HTTPError(404, "Book not found")
            return 200, {"message": "Book deleted"}
        finally:
            conn.close()


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def create_app(db_path=None):
    return BookApp(db_path or DEFAULT_DB)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = make_server(host, port, create_app(), server_class=ThreadingWSGIServer,
                         handler_class=QuietHandler)
    print(f"Serving on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
