"""HTTP layer: routing, JSON handling and the server factory."""

import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .store import BookStore
from .validation import ValidationError, validate_book

MAX_BODY_BYTES = 1024 * 1024
MAX_SQLITE_INT = 2**63 - 1

logger = logging.getLogger(__name__)


class HTTPError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict | None = None,
        headers: dict | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


# (path pattern, {HTTP method: handler method name})
ROUTES = [
    (re.compile(r"^/health$"), {"GET": "_health"}),
    (re.compile(r"^/books$"), {"GET": "_list_books", "POST": "_create_book"}),
    (
        re.compile(r"^/books/(?P<book_id>[^/]+)$"),
        {"GET": "_get_book", "PUT": "_update_book", "DELETE": "_delete_book"},
    ),
]


class BookAPIHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"

    # Every verb is routed through _dispatch so unknown methods on known paths
    # get a JSON 405 rather than the stdlib's HTML 501.
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

    def log_message(self, format, *args):
        logger.debug("%s - %s", self.address_string(), format % args)

    @property
    def store(self) -> BookStore:
        return self.server.store

    def _dispatch(self, method: str) -> None:
        url = urlsplit(self.path)
        path = url.path if url.path == "/" else url.path.rstrip("/")
        query = parse_qs(url.query)  # blank values are dropped, so ?author= means no filter
        try:
            for pattern, handlers in ROUTES:
                match = pattern.match(path)
                if match is None:
                    continue
                name = handlers.get(method)
                if name is None:
                    raise HTTPError(
                        405,
                        "method_not_allowed",
                        f"{method} is not allowed on {path}",
                        headers={"Allow": ", ".join(sorted(handlers))},
                    )
                getattr(self, name)(match.groupdict(), query)
                return
            raise HTTPError(404, "not_found", f"no route for {path}")
        except HTTPError as err:
            self._send_json(
                err.status,
                {"error": err.code, "message": err.message, **({"details": err.details} if err.details else {})},
                headers=err.headers,
            )
        except Exception:
            logger.exception("unhandled error handling %s %s", method, self.path)
            self._send_json(500, {"error": "internal_error", "message": "internal server error"})

    # --- handlers -----------------------------------------------------------

    def _health(self, params: dict, query: dict) -> None:
        try:
            self.store.ping()
        except Exception:
            logger.exception("health check failed")
            self._send_json(503, {"status": "unavailable", "database": "unavailable"})
            return
        self._send_json(200, {"status": "ok", "database": "ok"})

    def _list_books(self, params: dict, query: dict) -> None:
        author = query.get("author", [None])[0]
        self._send_json(200, self.store.list(author=author))

    def _create_book(self, params: dict, query: dict) -> None:
        book = self._validated_body()
        created = self.store.create(book)
        self._send_json(201, created, headers={"Location": f"/books/{created['id']}"})

    def _get_book(self, params: dict, query: dict) -> None:
        book = self.store.get(self._book_id(params))
        if book is None:
            raise self._not_found(params)
        self._send_json(200, book)

    def _update_book(self, params: dict, query: dict) -> None:
        book_id = self._book_id(params)
        book = self._validated_body()
        updated = self.store.update(book_id, book)
        if updated is None:
            raise self._not_found(params)
        self._send_json(200, updated)

    def _delete_book(self, params: dict, query: dict) -> None:
        if not self.store.delete(self._book_id(params)):
            raise self._not_found(params)
        self._send_empty(204)

    # --- helpers ------------------------------------------------------------

    def _book_id(self, params: dict) -> int:
        """Parse the id from the path. Anything that cannot be a row id is simply not found."""
        raw = params["book_id"]
        if not raw.isdecimal() or int(raw) > MAX_SQLITE_INT:
            raise self._not_found(params)
        return int(raw)

    def _not_found(self, params: dict) -> HTTPError:
        return HTTPError(404, "not_found", f"no book with id {params.get('book_id')}")

    def _validated_body(self) -> dict:
        try:
            payload = self._read_json()
        except ValueError:
            raise HTTPError(400, "invalid_json", "request body must be valid JSON")
        try:
            return validate_book(payload)
        except ValidationError as err:
            raise HTTPError(400, "validation_failed", "request validation failed", err.errors)

    def _read_json(self):
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise ValueError("missing body")
        try:
            length = int(length_header)
        except ValueError:
            raise ValueError("bad Content-Length")
        if length > MAX_BODY_BYTES:
            raise HTTPError(413, "payload_too_large", f"body exceeds {MAX_BODY_BYTES} bytes")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))  # UnicodeDecodeError is a ValueError

    def _send_json(self, status: int, payload, headers: dict | None = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()


class BookAPIServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: BookStore):
        super().__init__(address, BookAPIHandler)
        self.store = store


def create_server(host: str, port: int, db_path: str) -> BookAPIServer:
    """Build a server bound to ``host:port`` backed by the SQLite file at ``db_path``."""
    return BookAPIServer((host, port), BookStore(db_path))
