"""HTTP layer for the book collection API.

Built on the standard library (http.server + sqlite3), so it runs without
installing anything. Start it with:

    python app.py --port 8000 --db books.db
"""

import argparse
import json
import logging
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from db import Database
from validation import ValidationError, validate_book

logger = logging.getLogger(__name__)

BOOK_ID_PATH = re.compile(r"/books/([^/]+)")


class ApiError(Exception):
    """An error that maps directly to a JSON error response."""

    def __init__(self, status, message, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers or {}


def _not_found():
    return ApiError(404, "book not found")


def _method_not_allowed(allowed):
    return ApiError(405, "method not allowed", {"Allow": allowed})


def _parse_id(text):
    """Return the id as an int, or None if the path segment isn't a plain number."""
    if text.isascii() and text.isdigit():
        return int(text)
    return None


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_PATCH(self):
        # Defined so unsupported verbs get a JSON 405 instead of an HTML 501.
        self._handle("PATCH")

    def do_DELETE(self):
        self._handle("DELETE")

    def _handle(self, method):
        try:
            status, payload, headers = self._route(method)
        except ValidationError as exc:
            status = 400
            payload = {"error": "validation failed", "details": exc.fields}
            headers = {}
        except ApiError as exc:
            status, payload, headers = exc.status, {"error": exc.message}, exc.headers
        except Exception:
            logger.exception("unhandled error handling %s %s", method, self.path)
            status, payload, headers = 500, {"error": "internal server error"}, {}
        self._send_json(status, payload, headers)

    def _route(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"

        if path == "/health":
            if method != "GET":
                raise _method_not_allowed("GET")
            return self._health()

        if path == "/books":
            if method == "GET":
                return self._list_books(parse_qs(url.query, keep_blank_values=True))
            if method == "POST":
                return self._create_book()
            raise _method_not_allowed("GET, POST")

        match = BOOK_ID_PATH.fullmatch(path)
        if match:
            if method not in ("GET", "PUT", "DELETE"):
                raise _method_not_allowed("GET, PUT, DELETE")
            book_id = _parse_id(match.group(1))
            if book_id is None:
                raise _not_found()
            if method == "GET":
                return self._get_book(book_id)
            if method == "PUT":
                return self._update_book(book_id)
            return self._delete_book(book_id)

        raise ApiError(404, "not found")

    def _health(self):
        try:
            self.server.db.ping()
        except sqlite3.Error:
            return 503, {"status": "unavailable"}, {}
        return 200, {"status": "ok"}, {}

    def _list_books(self, query):
        author = query.get("author", [None])[0]
        if author is not None:
            author = author.strip()
            if not author:
                raise ApiError(400, "author filter must not be blank")
        return 200, self.server.db.list_books(author=author), {}

    def _create_book(self):
        book = self.server.db.create_book(validate_book(self._read_json()))
        return 201, book, {"Location": f"/books/{book['id']}"}

    def _get_book(self, book_id):
        book = self.server.db.get_book(book_id)
        if book is None:
            raise _not_found()
        return 200, book, {}

    def _update_book(self, book_id):
        # PUT replaces the whole record, so title and author are required again.
        book = self.server.db.update_book(book_id, validate_book(self._read_json()))
        if book is None:
            raise _not_found()
        return 200, book, {}

    def _delete_book(self, book_id):
        if not self.server.db.delete_book(book_id):
            raise _not_found()
        return 204, None, {}

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b""
            return json.loads(raw)
        except ValueError:
            # Covers bad Content-Length, invalid UTF-8 and invalid JSON.
            raise ApiError(400, "request body must be valid JSON")

    def _send_json(self, status, payload, headers):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        if body is not None:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body is not None:
            self.wfile.write(body)


class BookServer(ThreadingHTTPServer):
    def __init__(self, address, db):
        super().__init__(address, BookRequestHandler)
        self.db = db

    def server_close(self):
        super().server_close()
        self.db.close()


def create_server(db_path=":memory:", host="127.0.0.1", port=8000):
    """Build a server bound to host:port. Pass port=0 to pick a free port."""
    return BookServer((host, port), Database(db_path))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="SQLite database file")
    args = parser.parse_args(argv)

    server = create_server(args.db, args.host, args.port)
    host, port = server.server_address[:2]
    print(f"Serving books on http://{host}:{port} (database: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
