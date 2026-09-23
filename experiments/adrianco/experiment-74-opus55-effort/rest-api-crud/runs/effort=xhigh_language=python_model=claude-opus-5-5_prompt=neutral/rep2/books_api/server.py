"""HTTP transport built on the standard library's ``http.server``, plus the CLI entry point."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sqlite3
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .app import JSON_CONTENT_TYPE, BooksApp, Response
from .db import BookRepository

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 30


class BooksHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], app: BooksApp):
        self.app = app
        super().__init__(address, BooksRequestHandler)


class BooksRequestHandler(BaseHTTPRequestHandler):
    server: BooksHTTPServer
    protocol_version = "HTTP/1.1"  # keep-alive, so every response must be framed exactly
    server_version = "BooksAPI/1.0"
    # Socket timeout in seconds: stops idle keep-alive connections and stalled
    # uploads from holding a thread forever.
    timeout = REQUEST_TIMEOUT_SECONDS

    def _handle(self) -> None:
        body = self._read_body()
        if body is None:
            return
        response = self.server.app.handle(self.command, self.path, body)
        self._send(response, include_body=self.command != "HEAD")

    # BooksApp does the routing, including 405s, so every method goes to the same place.
    do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _handle

    def _read_body(self) -> bytes | None:
        """Read the request body. On a framing error, send the error response and return None."""
        if "Transfer-Encoding" in self.headers:
            self._send_error(411, "Chunked request bodies are not supported; send Content-Length")
            return None
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return b""
        try:
            length = int(raw_length)
            if length < 0:
                raise ValueError
        except ValueError:
            self._send_error(400, "Invalid Content-Length header")
            return None
        if length > MAX_BODY_BYTES:
            self._send_error(413, f"Request body exceeds {MAX_BODY_BYTES} bytes")
            return None
        try:
            body = self.rfile.read(length)
        except TimeoutError:
            self._send_error(408, "Timed out reading the request body")
            return None
        if len(body) < length:  # the client closed its side before sending the whole body
            self.close_connection = True
            return None
        return body

    def _send_error(self, status: int, message: str) -> None:
        # After a framing or protocol error the stream position is unknown (e.g. an
        # unread body is still on the socket), so the connection can't be reused.
        self._send(Response(status, {"error": message}), include_body=self.command != "HEAD", close=True)

    def _send(self, response: Response, *, include_body: bool = True, close: bool = False) -> None:
        body = response.body
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        if response.status != 204:  # a 204 response must not carry a body or Content-Length
            if body:
                self.send_header("Content-Type", JSON_CONTENT_TYPE)
            self.send_header("Content-Length", str(len(body)))
        if close:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        if include_body and body:
            self.wfile.write(body)

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """Replace the stdlib's HTML error page (malformed request line, etc.) with JSON."""
        self.log_error("code %d, message %s", code, message)
        self._send_error(code, message or HTTPStatus(code).phrase)

    def log_message(self, format: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


def create_server(app: BooksApp, host: str = "127.0.0.1", port: int = 8000) -> BooksHTTPServer:
    """Bind a server for ``app``. Pass ``port=0`` to have the OS choose a free port."""
    return BooksHTTPServer((host, port), app)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="books_api", description="Run the Books REST API.")
    # argparse applies `type` to string defaults, so bad env values get a clean error message.
    parser.add_argument(
        "--host", default=os.environ.get("BOOKS_API_HOST", "127.0.0.1"),
        help="interface to bind (env BOOKS_API_HOST, default 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=os.environ.get("BOOKS_API_PORT", "8000"),
        help="port to listen on, 0 for any free port (env BOOKS_API_PORT, default 8000)",
    )
    parser.add_argument(
        "--db", default=os.environ.get("BOOKS_DB_PATH", "books.db"),
        help="SQLite database file, or :memory: (env BOOKS_DB_PATH, default books.db)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        repository = BookRepository(args.db)
    except (OSError, sqlite3.Error) as exc:
        print(f"error: cannot open database {args.db!r}: {exc}", file=sys.stderr)
        return 1
    try:
        server = create_server(BooksApp(repository), args.host, args.port)
    except OSError as exc:
        repository.close()
        print(f"error: cannot listen on {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 1

    # Treat SIGTERM (docker stop, kill) like Ctrl+C so the socket and database close cleanly.
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

    host, port = server.server_address[:2]
    print(f"Books API listening on http://{host}:{port} (database: {args.db})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        repository.close()
    return 0
