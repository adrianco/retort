"""Command-line entry point: python -m bookapi"""

from __future__ import annotations

import argparse

from .server import create_server
from .store import BookStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    parser.add_argument("--db", default="books.db", help="SQLite database file (default: books.db)")
    args = parser.parse_args(argv)

    store = BookStore(args.db)
    server = create_server(store, args.host, args.port)
    print(f"Serving books on http://{args.host}:{server.server_port} (database: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
