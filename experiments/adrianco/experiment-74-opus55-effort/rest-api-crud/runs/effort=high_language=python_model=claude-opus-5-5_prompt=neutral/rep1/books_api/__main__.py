"""Run the books API: ``python -m books_api [--host HOST] [--port PORT] [--db PATH]``."""

import argparse
import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from books_api.app import create_app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def make_books_server(host, port, db_path, quiet=False):
    handler = WSGIRequestHandler
    if quiet:
        class QuietHandler(WSGIRequestHandler):
            def log_message(self, *args):
                pass
        handler = QuietHandler
    return make_server(host, port, create_app(db_path),
                       server_class=ThreadingWSGIServer, handler_class=handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("BOOKS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOOKS_PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", "books.db"),
                        help="SQLite database file (use :memory: for a throwaway DB)")
    args = parser.parse_args(argv)

    with make_books_server(args.host, args.port, args.db) as server:
        print(f"Serving books API on http://{args.host}:{args.port} (db: {args.db})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
