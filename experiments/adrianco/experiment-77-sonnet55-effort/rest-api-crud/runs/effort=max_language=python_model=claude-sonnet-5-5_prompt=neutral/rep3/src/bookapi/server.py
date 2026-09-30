"""Command-line entry point: serve the API with the standard library's WSGI server."""

from __future__ import annotations

import argparse
import logging
import os
import socket
import socketserver
import sqlite3
from typing import Callable, Optional, Sequence
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import create_app
from .repository import DEFAULT_DATABASE

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

logger = logging.getLogger(__name__)
access_logger = logging.getLogger(f"{__name__}.access")

# Request lines are attacker-controlled: escape anything that could forge log lines or
# smuggle terminal escape sequences into whoever reads the log.
_LOG_ESCAPES = {code: f"\\x{code:02x}" for code in (*range(0x20), *range(0x7F, 0xA0))}
_LOG_ESCAPES[ord("\\")] = "\\\\"


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    """A WSGI server that handles each request in its own thread."""

    daemon_threads = True  # don't let a slow client keep the process alive on shutdown
    request_queue_size = 128  # the socketserver default of 5 drops connections under bursts

    def server_bind(self) -> None:
        # ``HTTPServer.server_bind`` calls ``socket.getfqdn()``, a reverse-DNS lookup that
        # can stall start-up for seconds on misconfigured hosts. The name is only informational.
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = port
        self.setup_environ()


class RequestHandler(WSGIRequestHandler):
    timeout = 30  # seconds; drop stalled connections instead of tying up a thread forever

    def handle(self) -> None:
        try:
            super().handle()
        except socket.timeout:
            # Browsers open spare connections and never use them; that is not worth a traceback.
            logger.debug("Closing idle connection from %s", self.address_string())

    def log_message(self, format: str, *args: object) -> None:
        access_logger.info("%s - %s", self.address_string(), (format % args).translate(_LOG_ESCAPES))


def _non_blank(message: str) -> Callable[[str], str]:
    """An argparse ``type`` rejecting values that are empty but would silently mean something else."""

    def parse(value: str) -> str:
        if not value.strip():
            raise argparse.ArgumentTypeError(message)
        return value

    return parse


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid port {value!r}") from None
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be between 0 and 65535, got {port}")
    return port


def build_parser() -> argparse.ArgumentParser:
    """The command-line parser; environment variables supply the defaults.

    An environment variable that is set but empty counts as unset: an empty host would
    otherwise mean "every interface", and an empty database path a vanishing temp database.
    """
    parser = argparse.ArgumentParser(prog="bookapi", description="Serve the book collection REST API.")
    parser.add_argument(
        "--host",
        type=_non_blank("must not be empty; use 0.0.0.0 to listen on every interface"),
        default=os.environ.get("BOOKAPI_HOST") or DEFAULT_HOST,
        help="IPv4 interface to listen on (env BOOKAPI_HOST, default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=os.environ.get("BOOKAPI_PORT") or str(DEFAULT_PORT),
        help="port to listen on; 0 picks a free one (env BOOKAPI_PORT, default: %(default)s)",
    )
    parser.add_argument(
        "--db",
        type=_non_blank("must not be empty; use :memory: for a throw-away database"),
        default=os.environ.get("BOOKAPI_DB") or DEFAULT_DATABASE,
        help="path of the SQLite database file, created if missing (env BOOKAPI_DB, default: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="logging verbosity (default: %(default)s)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        app = create_app(args.db)
    except (OSError, sqlite3.Error) as exc:
        logger.error("Cannot open database %s: %s", args.db, exc)
        return 1
    try:
        try:
            server = make_server(args.host, args.port, app, ThreadingWSGIServer, RequestHandler)
        except OSError as exc:
            logger.error("Cannot listen on %s:%s: %s", args.host, args.port, exc)
            return 1
        with server:
            host, port = server.server_address[:2]
            logger.info("Serving %s on http://%s:%s (Ctrl+C to stop)", args.db, host, port)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down")
    finally:
        app.close()
    return 0
