"""HTTP server for the book collection API.

Uses only the standard library: ``http.server`` for transport, ``json`` for
bodies, and ``store.BookStore`` for persistence.

Run with ``python server.py --help`` for options.
"""

import argparse
import json
import logging
import re
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, NamedTuple
from urllib.parse import parse_qs, urlsplit

from store import BookStore
from validation import ValidationError, validate_book

LOGGER = logging.getLogger("books_api")

MAX_BODY_BYTES = 1024 * 1024
SQLITE_MAX_INTEGER = 2**63 - 1  # larger ids cannot exist, so they are simply not found
BOOK_PATH = re.compile(r"/books/([0-9]+)")  # [0-9] rather than \d, which also matches other scripts' digits


class Response(NamedTuple):
    status: int
    body: Any = None  # None means no body; only used for 204
    headers: dict[str, str] | None = None


class ApiError(Exception):
    """Raised inside a handler to send an error response."""

    def __init__(self, status: int, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"
    timeout = 30  # seconds; a stalled client cannot hold a thread forever

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")  # no handler, so this answers 405; partial updates go through PUT

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        # BaseHTTPRequestHandler calls this for malformed requests and unsupported
        # methods. Reply in the same JSON shape as every other error.
        self._send(Response(code, {"error": message or HTTPStatus(code).phrase}))

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s %s", self.address_string(), format % args)

    def _dispatch(self, method: str) -> None:
        try:
            response = self._route(method)
        except ValidationError as error:
            response = Response(400, {"error": "Validation failed", "details": error.errors})
        except ApiError as error:
            response = Response(error.status, {"error": error.message}, error.headers)
        except Exception:
            LOGGER.exception("Unhandled error for %s %s", method, self.path)
            response = Response(500, {"error": "Internal server error"})
        self._send(response)

    def _route(self, method: str) -> Response:
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        query = parse_qs(url.query)

        if path == "/health":
            handlers = {"GET": self._health}
        elif path == "/books":
            handlers = {"GET": lambda: self._list_books(query), "POST": self._create_book}
        else:
            match = BOOK_PATH.fullmatch(path)
            if match is None:
                raise ApiError(404, "Not found")
            book_id = int(match.group(1))
            if book_id > SQLITE_MAX_INTEGER:
                raise ApiError(404, "Book not found")
            handlers = {
                "GET": lambda: self._get_book(book_id),
                "PUT": lambda: self._update_book(book_id),
                "DELETE": lambda: self._delete_book(book_id),
            }

        handler = handlers.get(method)
        if handler is None:
            raise ApiError(405, "Method not allowed", {"Allow": ", ".join(sorted(handlers))})
        return handler()

    def _health(self) -> Response:
        try:
            self.server.store.ping()
        except sqlite3.Error:
            LOGGER.exception("Health check could not reach the database")
            return Response(503, {"status": "unavailable"})
        return Response(200, {"status": "ok"})

    def _list_books(self, query: dict[str, list[str]]) -> Response:
        author = query.get("author", [""])[0].strip()
        return Response(200, self.server.store.list_books(author=author or None))

    def _create_book(self) -> Response:
        fields = validate_book(self._read_json())
        book = self.server.store.create(**fields)
        return Response(201, book, {"Location": f"/books/{book['id']}"})

    def _get_book(self, book_id: int) -> Response:
        book = self.server.store.get(book_id)
        if book is None:
            raise ApiError(404, "Book not found")
        return Response(200, book)

    def _update_book(self, book_id: int) -> Response:
        changes = validate_book(self._read_json(), partial=True)
        book = self.server.store.update(book_id, changes)
        if book is None:
            raise ApiError(404, "Book not found")
        return Response(200, book)

    def _delete_book(self, book_id: int) -> Response:
        if not self.server.store.delete(book_id):
            raise ApiError(404, "Book not found")
        return Response(204)

    def _read_json(self) -> Any:
        content_type = self.headers.get("Content-Type")
        if content_type is not None and content_type.split(";")[0].strip().lower() != "application/json":
            raise ApiError(415, "Content-Type must be application/json")

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "Invalid Content-Length header") from None
        if length < 0:
            raise ApiError(400, "Invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise ApiError(413, f"Request body must be at most {MAX_BODY_BYTES} bytes")

        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (ValueError, RecursionError):  # bad JSON, or bad UTF-8, which json reports as ValueError
            raise ApiError(400, "Request body must be valid JSON") from None

    def _send(self, response: Response) -> None:
        self.send_response(response.status)
        for name, value in (response.headers or {}).items():
            self.send_header(name, value)
        if response.body is None:  # 204: no body and no Content-Length
            self.end_headers()
            return
        payload = json.dumps(response.body, ensure_ascii=False).encode("utf-8")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class BookHTTPServer(ThreadingHTTPServer):
    """Threaded server that gives each request handler access to the book store."""

    def __init__(self, address: tuple[str, int], store: BookStore) -> None:
        self.store = store
        super().__init__(address, BookRequestHandler)


def create_server(db_path: str, host: str = "127.0.0.1", port: int = 8000) -> BookHTTPServer:
    """Open the database at ``db_path`` and return a server bound to ``host:port``.

    Pass port 0 to let the OS pick a free port.
    """
    store = BookStore(db_path)
    try:
        return BookHTTPServer((host, port), store)
    except OSError:
        store.close()
        raise


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    parser.add_argument("--db", default="books.db", help="SQLite file, created if missing (default: books.db)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    server = create_server(args.db, args.host, args.port)
    LOGGER.info("Serving books on http://%s:%d (database: %s)", args.host, server.server_address[1], args.db)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down")
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
