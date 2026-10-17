"""HTTP layer: routing, JSON encoding and status codes, built on the standard library."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .storage import BookStore
from .validation import ValidationError, validate_book

MAX_BODY_BYTES = 1024 * 1024


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"

    @property
    def store(self):
        return self.server.store

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        # Not supported, but routed so unknown verbs get a JSON 405 instead of stdlib's HTML 501.
        self._dispatch("PATCH")

    def _dispatch(self, method):
        url = urlsplit(self.path)
        parts = [p for p in url.path.split("/") if p]

        if parts == ["health"]:
            return self._route(method, {"GET"}, lambda: self._health())

        if parts == ["books"]:
            return self._route(
                method,
                {"GET", "POST"},
                {
                    "GET": lambda: self._list_books(parse_qs(url.query)),
                    "POST": self._create_book,
                },
            )

        if len(parts) == 2 and parts[0] == "books":
            book_id = _parse_id(parts[1])
            if book_id is None:
                return self._error(404, "book not found")
            return self._route(
                method,
                {"GET", "PUT", "DELETE"},
                {
                    "GET": lambda: self._get_book(book_id),
                    "PUT": lambda: self._update_book(book_id),
                    "DELETE": lambda: self._delete_book(book_id),
                },
            )

        self._error(404, "not found")

    def _route(self, method, allowed, handlers):
        """Call the handler for ``method``. ``handlers`` may be a callable or a dict."""
        if method not in allowed:
            return self._send_json(
                405,
                {"error": f"method {method} not allowed"},
                headers={"Allow": ", ".join(sorted(allowed))},
            )
        handler = handlers if callable(handlers) else handlers[method]
        try:
            handler()
        except ValidationError as exc:
            self._error(400, "validation failed", details=exc.errors)
        except _BadRequest as exc:
            self._error(exc.status, str(exc))

    # --- handlers -----------------------------------------------------------

    def _health(self):
        try:
            self.store.ping()
        except Exception:  # noqa: BLE001 - any DB failure means unhealthy
            return self._send_json(503, {"status": "unavailable"})
        self._send_json(200, {"status": "ok"})

    def _list_books(self, query):
        author = query.get("author", [None])[0]
        self._send_json(200, self.store.list(author=author))

    def _get_book(self, book_id):
        book = self.store.get(book_id)
        if book is None:
            return self._error(404, "book not found")
        self._send_json(200, book)

    def _create_book(self):
        data = validate_book(self._read_json())
        book = self.store.create(data)
        self._send_json(201, book, headers={"Location": f"/books/{book['id']}"})

    def _update_book(self, book_id):
        data = validate_book(self._read_json())
        book = self.store.update(book_id, data)
        if book is None:
            return self._error(404, "book not found")
        self._send_json(200, book)

    def _delete_book(self, book_id):
        if not self.store.delete(book_id):
            return self._error(404, "book not found")
        self._send_empty(204)

    # --- helpers ------------------------------------------------------------

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            raise _BadRequest("invalid Content-Length header") from None
        if length > MAX_BODY_BYTES:
            raise _BadRequest("request body too large", status=413)
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise _BadRequest("invalid JSON body") from None

    def _error(self, status, message, details=None):
        payload = {"error": message}
        if details is not None:
            payload["details"] = details
        self._send_json(status, payload)

    def _send_json(self, status, payload, headers=None):
        self._write(_encode(payload), status, headers)

    def _send_empty(self, status):
        self._write(b"", status)

    def _write(self, body, status, headers=None):
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        if body:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 - matches base signature
        pass


class _BadRequest(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _parse_id(segment):
    try:
        value = int(segment)
    except ValueError:
        return None
    return value if value > 0 else None


def _encode(payload):
    return json.dumps(payload).encode("utf-8")


def create_server(host="127.0.0.1", port=8000, db_path=":memory:"):
    """Build (but do not start) an HTTP server bound to ``host:port``."""
    server = ThreadingHTTPServer((host, port), BookRequestHandler)
    server.store = BookStore(db_path)
    return server
