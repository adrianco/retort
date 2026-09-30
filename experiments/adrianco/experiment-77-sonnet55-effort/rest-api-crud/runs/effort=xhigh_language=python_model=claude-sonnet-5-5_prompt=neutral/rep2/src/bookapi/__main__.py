"""Command line entry point: ``python -m bookapi``."""

from __future__ import annotations

import argparse
import logging
import os

from .server import create_server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bookapi", description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", "books.db"), help="SQLite database file")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    httpd, store = create_server(args.host, args.port, args.db)
    host, port = httpd.server_address[:2]
    logging.getLogger("bookapi").info("serving on http://%s:%s (db: %s)", host, port, args.db)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        store.close()


if __name__ == "__main__":
    main()
