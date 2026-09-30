"""Run the API with ``python -m bookapi``."""

from __future__ import annotations

import argparse
import logging
import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from . import create_app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bookapi", description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", "books.db"),
                        help="SQLite database file (default: books.db)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    app = create_app(args.db)
    with make_server(args.host, args.port, app, server_class=ThreadingWSGIServer,
                     handler_class=WSGIRequestHandler) as server:
        print(f"Serving on http://{args.host}:{args.port} (db: {args.db})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down")


if __name__ == "__main__":
    main()
