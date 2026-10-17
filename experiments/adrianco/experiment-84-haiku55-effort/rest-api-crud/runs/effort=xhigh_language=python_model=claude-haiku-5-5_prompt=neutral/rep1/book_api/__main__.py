"""Command-line entry point: ``python -m book_api``."""

import argparse
import logging
from collections.abc import Sequence

from .repository import BookRepository
from .server import create_server


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="book_api", description="Run the book collection API.")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    parser.add_argument("--db", default="books.db", help="SQLite database file (default: books.db)")
    parser.add_argument(
        "--log-level",
        default="INFO",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="logging level (default: INFO)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    repository = BookRepository(args.db)
    server = create_server(repository, args.host, args.port)
    host, port = server.server_address[:2]
    print(f"Book API listening on http://{host}:{port} (database: {args.db})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down", flush=True)
    finally:
        server.server_close()
        repository.close()


if __name__ == "__main__":
    main()
