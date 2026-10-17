"""Command-line entry point: ``python -m bookapi``."""

from __future__ import annotations

import argparse
import logging
import os

from .api import BookApi
from .repository import BookRepository
from .server import make_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the book collection REST API.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_DB_PATH", "books.db"),
        help="SQLite database file (default: $BOOKS_DB_PATH or books.db)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    repository = BookRepository(args.db)
    server = make_server(BookApi(repository), args.host, args.port)
    print(
        f"Serving books on http://{args.host}:{server.server_port} (database: {args.db})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        repository.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
