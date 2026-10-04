"""Command-line entry point: serve the API with the standard library server."""

import argparse
import logging
import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from bookapi.app import BookAPI
from bookapi.store import BookStore


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Handle each request in its own thread so one slow client can't block others."""

    daemon_threads = True


def create_server(store: BookStore, host: str, port: int) -> WSGIServer:
    return make_server(host, port, BookAPI(store), server_class=ThreadingWSGIServer)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bookapi", description="Book collection REST API"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("BOOKS_HOST", "127.0.0.1"),
        help="interface to bind (env BOOKS_HOST, default 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("BOOKS_PORT", "8000"),
        help="port to listen on (env BOOKS_PORT, default 8000)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_DB", "books.db"),
        help="SQLite database file (env BOOKS_DB, default books.db)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    store = BookStore(args.db)
    try:
        with create_server(store, args.host, args.port) as server:
            host, port = server.server_address[:2]
            logging.getLogger(__name__).info(
                "Serving on http://%s:%s (database: %s)", host, port, args.db
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    finally:
        store.close()


if __name__ == "__main__":
    main()
