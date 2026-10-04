"""Command-line entry point: ``python -m books_api``."""

from __future__ import annotations

import argparse
import logging
import os
from socketserver import ThreadingMixIn
from typing import Optional, Sequence
from wsgiref.simple_server import WSGIServer, make_server

from .app import create_app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Handle each request in its own thread so one slow client cannot block others."""

    daemon_threads = True
    # The socketserver default backlog of 5 drops connections under bursts.
    request_queue_size = 128


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m books_api", description="Book collection REST API"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BOOKS_HOST", "127.0.0.1"),
        help="interface to bind (default: %(default)s, env: BOOKS_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("BOOKS_PORT", "8000"),
        help="port to listen on (default: %(default)s, env: BOOKS_PORT)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_DB", "books.db"),
        help="SQLite database file (default: %(default)s, env: BOOKS_DB)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app(args.db)
    with make_server(args.host, args.port, app, server_class=ThreadingWSGIServer) as server:
        host, port = server.server_address[:2]
        logging.info("Serving books API on http://%s:%s (database: %s)", host, port, args.db)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down")
        finally:
            app.repository.close()


if __name__ == "__main__":
    main()
