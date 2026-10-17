"""Command-line entry point: ``python -m books_api``."""

import argparse
import os

from .server import create_server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKS_DB_PATH", "books.db"),
        help="SQLite database file (default: $BOOKS_DB_PATH or books.db)",
    )
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port, args.db)
    host, port = server.server_address[:2]
    print(f"Serving books API on http://{host}:{port} (database: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
