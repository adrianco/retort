"""Standalone HTTP server for the book API."""

from __future__ import annotations

import argparse
import socketserver
import sys
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import create_app

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_DB = "books.db"


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    """Serve each request on its own thread so slow clients cannot block others."""

    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    """Request handler with a one-line log format (and none during tests)."""

    quiet = False

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        if not self.quiet:
            super().log_message(format, *args)


def make_http_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    db_path: str = DEFAULT_DB,
    quiet: bool = False,
) -> WSGIServer:
    """Create (but do not start) a threaded WSGI server for the API.

    Passing ``port=0`` binds an ephemeral port; read it back from
    ``server.server_address[1]``.
    """
    handler = type("Handler", (QuietHandler,), {"quiet": quiet})
    return make_server(
        host, port, create_app(db_path), ThreadingWSGIServer, handler
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bookapi", description="Book collection REST API"
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bind port")
    parser.add_argument(
        "--db", default=DEFAULT_DB, help="path to the SQLite database file"
    )
    args = parser.parse_args(argv)

    server = make_http_server(args.host, args.port, args.db)
    host, port = server.server_address[:2]
    print(f"Book API listening on http://{host}:{port} (database: {args.db})")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
