"""HTTP layer: routing, JSON handling and the stdlib server."""

import argparse
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .db import BookStore, IsbnConflictError
from .validation import validate_book

BOOK_ROUTE = re.compile(r"^/books/(\d+)$")


def _error(status, message, **extra):
    payload = {"error": message}
    payload.update(extra)
    return status, payload


class Api:
    """Framework-free request dispatcher. Returns ``(status, payload)`` tuples."""

    def __init__(self, store):
        self.store = store

    def handle(self, method, target, body=b""):
        parts = urlsplit(target)
        path = parts.path.rstrip("/") or "/"

        if path == "/health":
            if method != "GET":
                return _error(405, "method not allowed")
            return 200, {"status": "ok"}

        if path == "/books":
            if method == "GET":
                return self._list(parts.query)
            if method == "POST":
                return self._create(body)
            return _error(405, "method not allowed")

        match = BOOK_ROUTE.match(path)
        if match:
            book_id = int(match.group(1))
            if method == "GET":
                return self._get(book_id)
            if method == "PUT":
                return self._update(book_id, body)
            if method == "DELETE":
                return self._delete(book_id)
            return _error(405, "method not allowed")

        return _error(404, "not found")

    # -- handlers -----------------------------------------------------------

    def _list(self, query):
        author = parse_qs(query).get("author", [None])[0]
        books = self.store.list(author=author)
        return 200, {"books": books, "count": len(books)}

    def _create(self, body):
        data, errors = _parse_and_validate(body)
        if errors:
            return _error(400, "validation failed", details=errors)
        try:
            return 201, self.store.create(data)
        except IsbnConflictError:
            return _error(409, "a book with this isbn already exists")

    def _get(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            return _error(404, "book not found")
        return 200, book

    def _update(self, book_id, body):
        data, errors = _parse_and_validate(body)
        if errors:
            return _error(400, "validation failed", details=errors)
        try:
            book = self.store.update(book_id, data)
        except IsbnConflictError:
            return _error(409, "a book with this isbn already exists")
        if book is None:
            return _error(404, "book not found")
        return 200, book

    def _delete(self, book_id):
        if not self.store.delete(book_id):
            return _error(404, "book not found")
        return 200, {"deleted": True, "id": book_id}


def _parse_and_validate(body):
    try:
        data = json.loads(body.decode("utf-8") or "null")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, {"body": "must be valid JSON"}
    return validate_book(data)


class _Handler(BaseHTTPRequestHandler):
    def _respond(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        status, payload = self.server.api.handle(self.command, self.path, body)
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = _respond

    def log_message(self, format, *args):  # keep test output quiet
        pass


def make_server(store, host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), _Handler)
    server.api = Api(store)
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB_PATH", "books.db"))
    args = parser.parse_args(argv)

    store = BookStore(args.db)
    server = make_server(store, args.host, args.port)
    print(f"Serving on http://{args.host}:{args.port} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
