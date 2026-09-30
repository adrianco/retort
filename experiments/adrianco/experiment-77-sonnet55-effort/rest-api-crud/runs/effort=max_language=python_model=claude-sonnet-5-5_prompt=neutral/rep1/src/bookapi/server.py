"""Threaded HTTP server for the API, and the ``bookapi`` command-line entry point.

The server is the standard library's ``wsgiref`` with one thread per request. It is fine
for development and small deployments; for anything heavier run the WSGI application
(``bookapi.create_app``) under a production server such as gunicorn or waitress.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import signal
import socket
import sqlite3
import sys
import threading
from collections.abc import Iterator, Sequence
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import BookAPI
from .repository import DEFAULT_DATABASE, BookRepository
from .web import JSON_CONTENT_TYPE

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
REQUEST_TIMEOUT = 30  # seconds a client may stay silent before its connection is dropped

logger = logging.getLogger("bookapi.server")

# A logged request line is attacker-controlled: escape control characters (and backslashes, so
# the escapes stay unambiguous) so it cannot forge log entries or drive a terminal. Mirrors the
# stdlib's http.server, which older Python releases do not do.
_CONTROL_CHARS = {c: f"\\x{c:02x}" for c in (*range(32), *range(127, 160))}
_CONTROL_CHARS[ord("\\")] = "\\\\"


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """A WSGI server that handles each request in its own thread."""

    daemon_threads = True
    request_queue_size = 128  # the stdlib default of 5 drops connections in bursts


class RequestHandler(WSGIRequestHandler):
    """The HTTP layer: access logging, JSON protocol errors, and tolerance of bad clients."""

    timeout = REQUEST_TIMEOUT

    def handle(self) -> None:
        try:
            super().handle()
        except (socket.timeout, ConnectionError) as exc:
            # Routine (an idle browser connection, a dropped client), not a server error.
            logger.debug("Dropped connection from %s: %s", self.address_string(), exc)

    def log_message(self, format: str, *args: object) -> None:
        message = (format % args).translate(_CONTROL_CHARS)
        logger.info("%s %s", self.address_string(), message)

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """Answer requests the HTTP layer rejects itself (garbage request line, absurdly long
        URL, ...) with the same JSON error shape as the application, not the stdlib's HTML."""
        if message is None:
            message = self.responses.get(code, ("Error", ""))[0]
        self.log_error("code %d, message %s", code, message)
        if self.request_version == "HTTP/0.9":
            # Nothing usable was parsed, so the client's protocol is unknown. Some Python
            # releases (3.9.6 and 3.11.0 among them) then reply HTTP/0.9-style: a bare body
            # with no status line or headers. Always send a proper HTTP/1.0 reply instead.
            self.request_version = "HTTP/1.0"
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Connection", "close")
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def make_book_server(
    app: BookAPI, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
) -> WSGIServer:
    """Bind a threaded server for ``app``; call ``serve_forever()`` on it to start serving."""
    return make_server(
        host, port, app, server_class=ThreadingWSGIServer, handler_class=RequestHandler
    )


def _port(text: str) -> int:
    try:
        port = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid port: {text!r}") from None
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return port


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bookapi",
        description="Book collection REST API. Defaults can also be set with the "
        "BOOKS_HOST, BOOKS_PORT and BOOKS_DB environment variables.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BOOKS_HOST", DEFAULT_HOST),
        help="interface to listen on (default: %(default)s; use 0.0.0.0 to accept "
        "connections from other machines)",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=os.environ.get("BOOKS_PORT", str(DEFAULT_PORT)),
        help="port to listen on; 0 picks a free one (default: %(default)s)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_DB", DEFAULT_DATABASE),
        help="SQLite database file, created if missing (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    try:
        repository = BookRepository(args.db)
    except sqlite3.Error as exc:
        print(f"error: cannot open database {args.db!r}: {exc}", file=sys.stderr)
        return 1

    with repository:
        try:
            server = make_book_server(BookAPI(repository), args.host, args.port)
        except OSError as exc:
            print(f"error: cannot listen on {args.host}:{args.port}: {exc}", file=sys.stderr)
            return 1
        with server:
            _serve(server, args.db)
    return 0


def _raise_interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


@contextlib.contextmanager
def _sigterm_as_interrupt() -> Iterator[None]:
    """Treat SIGTERM (``kill``, ``docker stop``, systemd) like Ctrl+C, so shutdown is clean.

    SIGINT is deliberately left alone: shells start background jobs with it ignored, and
    that choice should be respected.
    """
    if threading.current_thread() is not threading.main_thread():
        yield  # signal handlers can only be installed from the main thread
        return
    previous = signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous if previous is not None else signal.SIG_DFL)


def _serve(server: WSGIServer, database: str) -> None:
    host, port = server.server_address[:2]
    logger.info(
        "Serving on http://%s:%s (database: %s) - press Ctrl+C to stop", host, port, database
    )
    with _sigterm_as_interrupt():
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down")
