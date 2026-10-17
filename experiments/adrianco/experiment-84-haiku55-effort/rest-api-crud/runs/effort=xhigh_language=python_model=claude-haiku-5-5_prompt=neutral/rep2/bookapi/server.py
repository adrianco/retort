"""HTTP transport: connects BooksApi to the standard library HTTP server."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import MAX_BODY_BYTES, BooksApi, Response
from .db import BookRepository


class BooksRequestHandler(BaseHTTPRequestHandler):
    server_version = "BooksAPI/1.0"

    def do_GET(self) -> None:
        self._handle()

    # Every verb takes the same path. BooksApi decides which ones are allowed.
    do_POST = do_PUT = do_DELETE = do_PATCH = do_GET

    def _handle(self) -> None:
        body = self._read_body()
        if body is None:
            return  # an error response has already been sent
        # http.server decodes the request line as latin-1. Re-decode it so a raw
        # UTF-8 query string (e.g. typed unencoded into curl) still matches.
        target = self.path.encode("latin-1").decode("utf-8", errors="replace")
        response = self.server.api.handle(self.command, target, body)
        self._send(response)

    def _read_body(self) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0:
            self._send(Response(400, {"error": "Invalid Content-Length header"}))
            return None
        if length > MAX_BODY_BYTES:
            # Reject before reading so an oversized upload is never buffered.
            self._send(Response(413, {"error": "Request body too large"}))
            return None
        return self.rfile.read(length)

    def _send(self, response: Response) -> None:
        payload = None if response.body is None else json.dumps(response.body).encode("utf-8")
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload is not None:
            self.wfile.write(payload)


class BooksHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server that owns the API and its database connection."""

    def __init__(self, address: tuple[str, int], api: BooksApi) -> None:
        super().__init__(address, BooksRequestHandler)
        self.api = api

    def server_close(self) -> None:
        super().server_close()
        self.api.close()


def create_server(host: str, port: int, db_path: str) -> BooksHTTPServer:
    """Build a server bound to host:port. Use port 0 to pick a free port."""
    return BooksHTTPServer((host, port), BooksApi(BookRepository(db_path)))
