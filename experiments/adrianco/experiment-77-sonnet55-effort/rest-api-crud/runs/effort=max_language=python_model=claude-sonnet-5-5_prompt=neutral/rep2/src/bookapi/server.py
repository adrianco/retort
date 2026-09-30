"""Command-line entry point: serve the WSGI app with the standard-library server."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import socketserver
import sqlite3
import sys
from collections.abc import Sequence
from typing import Any
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import DEFAULT_DATABASE, BookApp, create_app

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("bookapi.access")

# Control characters (C0 and C1) are escaped in log lines, so that a crafted request
# cannot forge log entries or smuggle terminal escape sequences into them.
_CONTROL_CHARS = {code: f"\\x{code:02x}" for code in (*range(32), *range(127, 160))}

_NON_ASCII = re.compile(rb"[\x80-\xff]")


class RequestHandler(WSGIRequestHandler):
    """Request handler of the built-in server.

    Compared with the standard one it logs through :mod:`logging`, answers
    protocol-level failures (a malformed request line, oversized headers, ...) in JSON
    like the application does, drops stalled clients, and copes with raw UTF-8 in URLs.
    """

    # Give up on a client that connects and then goes quiet, instead of holding a thread
    # for it forever. A body that stalls half-way is answered with 408 by the app.
    timeout = 30

    raw_requestline: bytes  # set by the base class before it calls parse_request()

    def parse_request(self) -> bool:
        # http.server decodes the request line as latin-1 and then splits it on *Unicode*
        # whitespace, so the UTF-8 bytes of "à" (C3 A0) or "х" (D1 85) read as NBSP / NEL
        # and cut the URL short. Percent-encoding every non-ASCII byte first, as a
        # well-behaved client would have, avoids that; the app decodes it as UTF-8 again.
        self.raw_requestline = _NON_ASCII.sub(
            lambda match: b"%%%02X" % match.group()[0], self.raw_requestline
        )
        return super().parse_request()

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        """Report protocol-level failures as JSON, like every other error."""
        if self.request_version == "HTTP/0.9":
            # The request line was too broken to tell what the client speaks. Older
            # Pythons then answer HTTP/0.9-style: a bare body with no status line or
            # headers. Reply properly instead, as wsgiref does for normal responses.
            self.request_version = "HTTP/1.0"
        phrase = self.responses.get(code, ("Error", ""))[0]
        detail = message or phrase
        body = json.dumps({"error": detail}).encode("utf-8")
        self.log_error("code %d, message %s", code, detail)
        self.send_response(code, phrase)
        self.send_header("Connection", "close")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        message = (format % args).translate(_CONTROL_CHARS)
        access_logger.info("%s %s", self.address_string(), message)


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    """A WSGI server that handles each connection in its own thread."""

    daemon_threads = True
    # The default backlog of 5 can refuse connections when many clients arrive at once.
    request_queue_size = 128

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Log failures with :mod:`logging`; a client that hangs up or stalls is routine."""
        error = sys.exc_info()[1]
        if isinstance(error, (ConnectionError, socket.timeout)):
            logger.debug("Connection from %s ended early: %r", client_address[0], error)
        else:
            logger.error("Error while serving %s", client_address[0], exc_info=True)


def create_server(app: BookApp, host: str, port: int) -> WSGIServer:
    """Bind a threaded server for ``app``. Port 0 picks a free port."""
    return make_server(
        host, port, app, server_class=ThreadingWSGIServer, handler_class=RequestHandler
    )


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid port: {value!r}") from None
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be between 0 and 65535, got {port}")
    return port


def _database(value: str) -> str:
    if not value.strip():
        # SQLite would quietly open a temporary database that vanishes on exit.
        raise argparse.ArgumentTypeError("the database path must not be empty")
    return value


def build_parser() -> argparse.ArgumentParser:
    """Command-line options; each falls back to an environment variable, then a default.

    An environment variable that is set but empty counts as unset.
    """
    parser = argparse.ArgumentParser(
        prog="bookapi", description="Serve the book collection REST API."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BOOKS_HOST") or DEFAULT_HOST,
        help="address to listen on (env BOOKS_HOST, default %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=os.environ.get("BOOKS_PORT") or DEFAULT_PORT,
        help="port to listen on; 0 picks a free one (env BOOKS_PORT, default %(default)s)",
    )
    parser.add_argument(
        "--db",
        type=_database,
        default=os.environ.get("BOOKS_DB") or DEFAULT_DATABASE,
        help="SQLite database file, created if missing (env BOOKS_DB, default %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the server until interrupted. Returns the process exit status."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    try:
        app = create_app(args.db)
    except sqlite3.Error as exc:
        logger.error("Cannot open database %r: %s", args.db, exc)
        return 1

    try:
        server = create_server(app, args.host, args.port)
    except OSError as exc:
        logger.error("Cannot listen on %s:%s: %s", args.host, args.port, exc)
        app.repository.close()
        return 1

    host, port = server.server_address[:2]
    logger.info("Serving on http://%s:%s (database: %s); Ctrl+C to stop", host, port, args.db)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        server.server_close()
        app.repository.close()
    return 0
