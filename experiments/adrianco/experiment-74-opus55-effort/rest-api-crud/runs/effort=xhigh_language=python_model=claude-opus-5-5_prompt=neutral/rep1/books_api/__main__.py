"""Command-line entry point: ``python -m books_api``."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys

from .app import BooksApp
from .repository import BookRepository
from .server import make_server

logger = logging.getLogger("books_api")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m books_api", description="Run the book collection REST API."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BOOKS_API_HOST", "127.0.0.1"),
        help="interface to bind (env BOOKS_API_HOST, default 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("BOOKS_API_PORT", "8000"),
        help="port to listen on, 0 for any free port (env BOOKS_API_PORT, default 8000)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_API_DB", "books.db"),
        help='SQLite database file, or ":memory:" (env BOOKS_API_DB, default books.db)',
    )
    return parser.parse_args(argv)


def _stop_on_sigterm(signum: int, frame: object) -> None:
    # Turn SIGTERM (docker stop, systemd, kill) into the same clean shutdown as Ctrl+C.
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    signal.signal(signal.SIGTERM, _stop_on_sigterm)

    repository = BookRepository(args.db)
    try:
        with make_server(args.host, args.port, BooksApp(repository)) as server:
            logger.info(
                "Serving on http://%s:%d (database: %s)", args.host, server.server_port, args.db
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down")
    finally:
        repository.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
