"""Command-line entry point: ``python -m bookapi``."""

import argparse

from .server import create_server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default="books.db", help="SQLite file path")
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port, args.db)
    print(f"Serving books on http://{args.host}:{server.server_address[1]} (db: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
