"""HTTP layer: routing, JSON encoding and status codes."""

import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .store import BookStore, DuplicateISBNError
from .validation import ValidationError, validate_book

MAX_BODY_BYTES = 64 * 1024
_BOOK_PATH = re.compile(r"^/books/(\d+)$")


class HTTPError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BooksAPI/1.0"
    protocol_version = "HTTP/1.1"

    # --- dispatch -------------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def _dispatch(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        query = parse_qs(url.query)
        self._body_consumed = False
        try:
            if path == "/health":
                routes = {"GET": self._health}
                args = ()
            elif path == "/books":
                routes = {"GET": lambda: self._list_books(query), "POST": self._create_book}
                args = ()
            elif match := _BOOK_PATH.match(path):
                routes = {
                    "GET": self._get_book,
                    "PUT": self._update_book,
                    "DELETE": self._delete_book,
                }
                args = (int(match.group(1)),)
            else:
                raise HTTPError(HTTPStatus.NOT_FOUND, "Not found")

            handler = routes.get(method)
            if handler is None:
                raise HTTPError(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "Method not allowed",
                    {"allowed": sorted(routes)},
                )
            handler(*args)
        except HTTPError as exc:
            body = {"error": exc.message}
            if exc.details is not None:
                body["details"] = exc.details
            headers = {}
            if not self._body_consumed and self.headers.get("Content-Length", "0") != "0":
                # Unread body bytes would corrupt the next keep-alive request.
                self.close_connection = True
            if exc.status == HTTPStatus.METHOD_NOT_ALLOWED:
                headers["Allow"] = ", ".join(exc.details["allowed"])
            self._send_json(exc.status, body, headers)
        except Exception:
            self.log_error("Unhandled error processing %s %s", method, self.path)
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})

    # --- handlers -------------------------------------------------------

    @property
    def store(self) -> BookStore:
        return self.server.store

    def _health(self):
        try:
            self.store.ping()
        except Exception:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "database": "unavailable"}
            )
            return
        self._send_json(HTTPStatus.OK, {"status": "ok", "database": "ok"})

    def _list_books(self, query):
        author = query.get("author", [None])[0]
        self._send_json(HTTPStatus.OK, self.store.list(author=author))

    def _get_book(self, book_id):
        self._send_json(HTTPStatus.OK, self._require_book(book_id))

    def _create_book(self):
        book = self._validated_body()
        try:
            created = self.store.create(book)
        except DuplicateISBNError:
            raise HTTPError(HTTPStatus.CONFLICT, "A book with this ISBN already exists")
        self._send_json(HTTPStatus.CREATED, created, {"Location": f"/books/{created['id']}"})

    def _update_book(self, book_id):
        self._require_book(book_id)
        book = self._validated_body(book_id)
        try:
            updated = self.store.update(book_id, book)
        except DuplicateISBNError:
            raise HTTPError(HTTPStatus.CONFLICT, "A book with this ISBN already exists")
        if updated is None:
            raise HTTPError(HTTPStatus.NOT_FOUND, "Book not found")
        self._send_json(HTTPStatus.OK, updated)

    def _delete_book(self, book_id):
        if not self.store.delete(book_id):
            raise HTTPError(HTTPStatus.NOT_FOUND, "Book not found")
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # --- helpers --------------------------------------------------------

    def _require_book(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            raise HTTPError(HTTPStatus.NOT_FOUND, "Book not found")
        return book

    def _validated_body(self, book_id=None):
        payload = self._read_json()
        if isinstance(payload, dict) and "id" in payload and book_id is not None:
            if payload["id"] != book_id:
                raise HTTPError(
                    HTTPStatus.BAD_REQUEST,
                    "Validation failed",
                    {"id": "Body id does not match URL id"},
                )
        try:
            return validate_book(payload)
        except ValidationError as exc:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Validation failed", exc.errors)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise HTTPError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body too large")
        if length <= 0:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body is required")
        raw = self.rfile.read(length)
        self._body_consumed = True
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON")

    def _send_json(self, status, body, headers=None):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        if not getattr(self.server, "quiet", False):
            super().log_message(format, *args)


class BookServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, quiet=False):
        super().__init__(address, BookRequestHandler)
        self.store = store
        self.quiet = quiet


def create_server(host="127.0.0.1", port=8000, db_path="books.db", quiet=False):
    """Create (but do not start) a server backed by the SQLite file at ``db_path``."""
    return BookServer((host, port), BookStore(db_path), quiet=quiet)
