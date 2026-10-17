"""HTTP layer: routing, JSON encoding and error handling on top of http.server."""

import json
import logging
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .database import BookRepository, ConflictError
from .validation import ValidationError, validate_book

MAX_BODY_BYTES = 1024 * 1024
_BOOK_PATH = re.compile(r"/books/(\d+)")

logger = logging.getLogger(__name__)


class HTTPError(Exception):
    def __init__(self, status, message, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers or {}


class BookAPIHandler(BaseHTTPRequestHandler):
    server_version = "BooksAPI/1.0"

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):  # not supported, but routed so unsupported methods get our 405
        self._dispatch("PATCH")

    @property
    def repository(self):
        return self.server.repository

    def _dispatch(self, method):
        url = urlsplit(self.path)
        try:
            if url.path == "/health":
                self._require_method(method, ("GET",))
                self._health()
            elif url.path == "/books":
                self._require_method(method, ("GET", "POST"))
                if method == "GET":
                    self._list_books(url.query)
                else:
                    self._create_book()
            elif match := _BOOK_PATH.fullmatch(url.path):
                self._require_method(method, ("GET", "PUT", "DELETE"))
                book_id = int(match.group(1))
                if method == "GET":
                    self._get_book(book_id)
                elif method == "PUT":
                    self._update_book(book_id)
                else:
                    self._delete_book(book_id)
            else:
                raise HTTPError(404, "not found")
        except HTTPError as exc:
            self._send_json(exc.status, {"error": exc.message}, exc.headers)
        except ValidationError as exc:
            self._send_json(400, {"error": "validation failed", "details": exc.errors})
        except ConflictError:
            self._send_json(409, {"error": "a book with this ISBN already exists"})
        except Exception:
            logger.exception("unhandled error handling %s %s", method, self.path)
            self._send_json(500, {"error": "internal server error"})

    def _require_method(self, method, allowed):
        if method not in allowed:
            raise HTTPError(405, "method not allowed", {"Allow": ", ".join(allowed)})

    def _health(self):
        try:
            self.repository.ping()
        except sqlite3.Error:
            self._send_json(503, {"status": "unavailable"})
        else:
            self._send_json(200, {"status": "ok"})

    def _list_books(self, query):
        params = parse_qs(query, keep_blank_values=True)
        author = None
        if "author" in params:
            author = params["author"][0].strip()
            if not author:
                raise HTTPError(400, "author filter must not be blank")
        self._send_json(200, self.repository.find(author=author))

    def _create_book(self):
        book = validate_book(self._read_json())
        created = self.repository.create(book)
        self._send_json(201, created, {"Location": f"/books/{created['id']}"})

    def _get_book(self, book_id):
        book = self.repository.get(book_id)
        if book is None:
            raise HTTPError(404, "book not found")
        self._send_json(200, book)

    def _update_book(self, book_id):
        book = validate_book(self._read_json())
        updated = self.repository.update(book_id, book)
        if updated is None:
            raise HTTPError(404, "book not found")
        self._send_json(200, updated)

    def _delete_book(self, book_id):
        if not self.repository.delete(book_id):
            raise HTTPError(404, "book not found")
        self._send(204)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise HTTPError(400, "invalid Content-Length header")
        if length < 0:
            raise HTTPError(400, "invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise HTTPError(413, "request body too large")
        try:
            return json.loads(self.rfile.read(length))
        except ValueError:  # covers JSONDecodeError and UnicodeDecodeError
            raise HTTPError(400, "request body must be valid JSON")

    def _send_json(self, status, payload, headers=None):
        body = json.dumps(payload).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", headers)

    def _send(self, status, body=b"", content_type=None, headers=None):
        self.send_response(status)
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)


class BookAPIServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, repository):
        self.repository = repository
        super().__init__(address, BookAPIHandler)

    def server_close(self):
        super().server_close()
        self.repository.close()


def create_server(host="127.0.0.1", port=8000, db_path="books.db"):
    """Build a server bound to host:port. Pass port 0 to let the OS pick a free port."""
    return BookAPIServer((host, port), BookRepository(db_path))
