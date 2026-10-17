"""HTTP transport: connects the standard library HTTP server to ``BookApi``."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import BookApi, Response

MAX_BODY_BYTES = 64 * 1024

log = logging.getLogger(__name__)


class BookHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], api: BookApi):
        super().__init__(address, BookRequestHandler)
        self.api = api


class BookRequestHandler(BaseHTTPRequestHandler):
    server_version = "BookAPI/1.0"
    server: BookHTTPServer

    def do_GET(self) -> None:
        self._dispatch()

    do_POST = do_PUT = do_DELETE = do_PATCH = do_GET

    def _dispatch(self) -> None:
        # Bodies are read with Content-Length only; the connection closes after each
        # response (HTTP/1.0), so an unread body never leaks into the next request.
        if self.headers.get("Transfer-Encoding"):
            self._send(Response(501, {"error": "Transfer-Encoding is not supported"}))
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0:
            self._send(Response(400, {"error": "Invalid Content-Length"}))
            return
        if length > MAX_BODY_BYTES:
            self._send(Response(413, {"error": "Request body is too large"}))
            return

        body = self.rfile.read(length) if length else b""
        self._send(self.server.api.handle(self.command, self.path, body))

    def _send(self, response: Response) -> None:
        payload = b"" if response.body is None else json.dumps(response.body).encode("utf-8")
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        if payload:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        # RFC 9110: a 204 response must not carry a Content-Length header.
        if response.status != 204:
            self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        log.info("%s - %s", self.address_string(), format % args)


def make_server(api: BookApi, host: str = "127.0.0.1", port: int = 8000) -> BookHTTPServer:
    """Bind a server for ``api``. Pass port 0 to let the OS pick a free port."""
    return BookHTTPServer((host, port), api)
