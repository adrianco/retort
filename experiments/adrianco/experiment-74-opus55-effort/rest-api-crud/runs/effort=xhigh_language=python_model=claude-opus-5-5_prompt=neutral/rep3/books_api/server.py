"""Run the API with the standard library's WSGI server.

    python -m books_api --host 127.0.0.1 --port 8000 --db books.db
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import socketserver
import sqlite3
from collections.abc import Sequence
from wsgiref.simple_server import WSGIServer, make_server

from .app import BookAPI
from .storage import BookRepository

logger = logging.getLogger(__name__)


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    """wsgiref's server, handling each request in its own thread."""

    daemon_threads = True


def create_server(app: BookAPI, host: str, port: int) -> ThreadingWSGIServer:
    return make_server(host, port, app, server_class=ThreadingWSGIServer)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument(
        "--host",
        default=os.environ.get("BOOKS_API_HOST", "127.0.0.1"),
        help="interface to bind (env: BOOKS_API_HOST, default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("BOOKS_API_PORT", "8000"),
        help="port to listen on (env: BOOKS_API_PORT, default: 8000)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_API_DB", "books.db"),
        help="SQLite database file (env: BOOKS_API_DB, default: books.db)",
    )
    return parser.parse_args(argv)


def _interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    # Treat SIGTERM (docker stop, systemd, ...) like Ctrl+C: stop cleanly.
    signal.signal(signal.SIGTERM, _interrupt)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        repository = BookRepository(args.db)
    except (OSError, sqlite3.Error) as exc:
        logger.error("Cannot open database %s: %s", args.db, exc)
        return 1
    try:
        try:
            httpd = create_server(BookAPI(repository), args.host, args.port)
        except OSError as exc:
            logger.error("Cannot listen on %s:%s: %s", args.host, args.port, exc.strerror or exc)
            return 1
        with httpd:
            host, port = httpd.server_address[:2]
            logger.info("Serving on http://%s:%s (database: %s)", host, port, args.db)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down")
    finally:
        repository.close()
    return 0
