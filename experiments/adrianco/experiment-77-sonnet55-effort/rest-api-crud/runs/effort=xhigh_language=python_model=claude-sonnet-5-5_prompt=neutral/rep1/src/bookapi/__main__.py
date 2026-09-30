"""Run the API with the built-in threaded WSGI server: ``python -m bookapi``."""

import argparse
import logging
import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from .app import create_app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bookapi", description=__doc__)
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_DB_PATH", "books.db"),
        help="SQLite database file (default: books.db, or $BOOKS_DB_PATH)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app(args.db)
    with make_server(args.host, args.port, app, server_class=ThreadingWSGIServer) as server:
        logging.info("Serving on http://%s:%s (db: %s)", args.host, args.port, args.db)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down")
        finally:
            app.close()


if __name__ == "__main__":
    main()
