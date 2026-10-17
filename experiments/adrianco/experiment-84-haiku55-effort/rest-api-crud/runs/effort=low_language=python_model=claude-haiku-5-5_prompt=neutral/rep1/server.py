"""HTTP layer for the book collection API, built on the standard library only."""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from book_store import BookStore, ValidationError

BOOK_ID_PATH = re.compile(r"^/books/(\d+)$")
MAX_BODY_BYTES = 1_000_000


class BookRequestHandler(BaseHTTPRequestHandler):
    # Set by make_server().
    store: BookStore

    server_version = "BookAPI/1.0"

    # ----- routing -----

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"

        if path == "/health":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._send_json(200, {"status": "ok"})

        if path == "/books":
            if method == "GET":
                return self._list_books(url.query)
            if method == "POST":
                return self._create_book()
            return self._method_not_allowed("GET, POST")

        match = BOOK_ID_PATH.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                return self._get_book(book_id)
            if method == "PUT":
                return self._update_book(book_id)
            if method == "DELETE":
                return self._delete_book(book_id)
            return self._method_not_allowed("GET, PUT, DELETE")

        return self._send_json(404, {"error": "not found"})

    # ----- handlers -----

    def _list_books(self, query_string):
        params = parse_qs(query_string)
        author = params.get("author", [None])[0]
        if author is not None and not author.strip():
            return self._send_json(400, {"error": "author filter must not be empty"})
        books = self.store.list(author=author)
        return self._send_json(200, books)

    def _create_book(self):
        data = self._read_json()
        if data is None:
            return
        try:
            book = self.store.create(data)
        except ValidationError as exc:
            return self._send_json(400, {"error": "validation failed", "details": exc.errors})
        return self._send_json(201, book, location=f"/books/{book['id']}")

    def _get_book(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            return self._not_found(book_id)
        return self._send_json(200, book)

    def _update_book(self, book_id):
        data = self._read_json()
        if data is None:
            return
        try:
            book = self.store.update(book_id, data)
        except ValidationError as exc:
            return self._send_json(400, {"error": "validation failed", "details": exc.errors})
        if book is None:
            return self._not_found(book_id)
        return self._send_json(200, book)

    def _delete_book(self, book_id):
        if not self.store.delete(book_id):
            return self._not_found(book_id)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ----- helpers -----

    def _not_found(self, book_id):
        return self._send_json(404, {"error": f"book {book_id} not found"})

    def _method_not_allowed(self, allowed):
        return self._send_json(405, {"error": "method not allowed"}, extra_headers={"Allow": allowed})

    def _read_json(self):
        """Parse the request body as JSON. Sends a 400/413 and returns None on failure."""
        length = self.headers.get("Content-Length")
        try:
            length = int(length) if length is not None else 0
        except ValueError:
            length = -1
        if length < 0:
            self._send_json(400, {"error": "invalid Content-Length"})
            return None
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "request body too large"})
            return None
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "request body must be valid JSON"})
            return None

    def _send_json(self, status, payload, location=None, extra_headers=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if location:
            self.send_header("Location", location)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # keep test output quiet
        if os.environ.get("BOOKAPI_QUIET") == "1":
            return
        super().log_message(format, *args)


def make_server(db_path="books.db", host="127.0.0.1", port=8000):
    """Build a threaded HTTP server bound to a BookStore at db_path."""
    store = BookStore(db_path)
    handler = type("Handler", (BookRequestHandler,), {"store": store})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.store = store
    return httpd


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    db_path = os.environ.get("DATABASE_PATH", "books.db")
    httpd = make_server(db_path, host, port)
    print(f"Book API listening on http://{host}:{port} (db: {db_path})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        httpd.store.close()


if __name__ == "__main__":
    main()
