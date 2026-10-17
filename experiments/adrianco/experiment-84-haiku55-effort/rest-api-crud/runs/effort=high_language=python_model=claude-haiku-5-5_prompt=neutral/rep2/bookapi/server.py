"""HTTP layer for the book API.

`handle_request` maps (method, target, body) to a `Response` without touching
sockets, so routing can be tested directly. `create_server` binds it to the
standard library's threaded HTTP server.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .store import BookStore
from .validation import ValidationError, validate_book

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 1_000_000
_MAX_ID = 2**63 - 1  # SQLite INTEGER limit; larger path ids can't match any row.
_BOOK_PATH = re.compile(r"/books/([0-9]+)")


@dataclass
class Response:
    status: int
    body: object = None
    headers: dict[str, str] = field(default_factory=dict)


def handle_request(store: BookStore, method: str, target: str, raw_body: bytes = b"") -> Response:
    parts = urlsplit(target)
    path = parts.path.rstrip("/") or "/"
    query = parse_qs(parts.query, keep_blank_values=True)
    try:
        return _route(store, method, path, query, raw_body)
    except ValidationError as exc:
        return _error(400, "Validation failed", exc.errors)


def _route(
    store: BookStore, method: str, path: str, query: dict[str, list[str]], raw_body: bytes
) -> Response:
    if path == "/health":
        return _health(store) if method == "GET" else _method_not_allowed("GET")

    if path == "/books":
        if method == "GET":
            return _list_books(store, query)
        if method == "POST":
            return _create_book(store, raw_body)
        return _method_not_allowed("GET, POST")

    match = _BOOK_PATH.fullmatch(path)
    if match:
        book_id = int(match.group(1))
        if book_id > _MAX_ID:
            return _error(404, "Book not found")
        if method == "GET":
            return _get_book(store, book_id)
        if method == "PUT":
            return _replace_book(store, book_id, raw_body)
        if method == "DELETE":
            return _delete_book(store, book_id)
        return _method_not_allowed("GET, PUT, DELETE")

    return _error(404, "Not found")


def _health(store: BookStore) -> Response:
    try:
        store.ping()
    except sqlite3.Error:
        log.exception("health check failed")
        return Response(503, {"status": "unavailable"})
    return Response(200, {"status": "ok"})


def _list_books(store: BookStore, query: dict[str, list[str]]) -> Response:
    author = None
    if "author" in query:
        author = query["author"][-1].strip()
        if not author:
            raise ValidationError({"author": "must not be blank"})
    return Response(200, store.list_books(author))


def _create_book(store: BookStore, raw_body: bytes) -> Response:
    created = store.create(validate_book(_parse_json(raw_body)))
    return Response(201, created, {"Location": f"/books/{created['id']}"})


def _get_book(store: BookStore, book_id: int) -> Response:
    book = store.get(book_id)
    return Response(200, book) if book else _error(404, "Book not found")


def _replace_book(store: BookStore, book_id: int, raw_body: bytes) -> Response:
    updated = store.update(book_id, validate_book(_parse_json(raw_body)))
    return Response(200, updated) if updated else _error(404, "Book not found")


def _delete_book(store: BookStore, book_id: int) -> Response:
    if store.delete(book_id):
        return Response(204)
    return _error(404, "Book not found")


def _parse_json(raw_body: bytes) -> object:
    try:
        return json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValidationError({"body": "must be valid JSON"}) from None


def _error(status: int, message: str, details: dict[str, str] | None = None) -> Response:
    body: dict[str, object] = {"error": message}
    if details:
        body["details"] = details
    return Response(status, body)


def _method_not_allowed(allowed: str) -> Response:
    response = _error(405, "Method not allowed")
    response.headers["Allow"] = allowed
    return response


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"
    store: BookStore  # bound per server in create_server()

    def _dispatch(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0:
            self._send(_error(400, "Invalid Content-Length header"))
            return
        if length > MAX_BODY_BYTES:
            # The unread body would corrupt the next request on this connection.
            self.close_connection = True
            self._send(_error(413, "Request body too large"))
            return

        raw_body = self.rfile.read(length) if length else b""
        try:
            response = handle_request(self.store, self.command, self.path, raw_body)
        except Exception:
            log.exception("unhandled error for %s %s", self.command, self.path)
            response = _error(500, "Internal server error")
        self._send(response)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _dispatch

    def _send(self, response: Response) -> None:
        payload = b"" if response.body is None else json.dumps(response.body).encode("utf-8")
        self.send_response(response.status)
        if payload:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)


def create_server(store: BookStore, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    """Build (but do not start) an HTTP server. Pass port 0 to pick a free port."""
    handler = type("BoundBookRequestHandler", (BookRequestHandler,), {"store": store})
    return ThreadingHTTPServer((host, port), handler)
