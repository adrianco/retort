"""Command-line entry point that serves the API with the standard library WSGI server."""

import argparse
import os
import socketserver
from wsgiref.simple_server import WSGIServer, make_server

from .app import BookApp
from .store import BookStore

DEFAULT_DB_PATH = "books.db"


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_DB_PATH", DEFAULT_DB_PATH),
        help="SQLite database file (default: $BOOKS_DB_PATH or books.db)",
    )
    args = parser.parse_args(argv)

    store = BookStore(args.db)
    try:
        with make_server(args.host, args.port, BookApp(store), server_class=ThreadingWSGIServer) as httpd:
            print(f"Serving book API on http://{args.host}:{args.port} (database: {args.db})")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("Shutting down")
    finally:
        store.close()
