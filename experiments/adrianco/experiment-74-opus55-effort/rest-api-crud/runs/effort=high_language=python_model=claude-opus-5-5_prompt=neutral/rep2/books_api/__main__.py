"""Run the API: ``python -m books_api [--host H] [--port P] [--db PATH]``."""

import argparse
import os

from .server import create_server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("BOOKS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOOKS_PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKS_DB", "books.db"))
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
        server.store.close()


if __name__ == "__main__":
    main()
