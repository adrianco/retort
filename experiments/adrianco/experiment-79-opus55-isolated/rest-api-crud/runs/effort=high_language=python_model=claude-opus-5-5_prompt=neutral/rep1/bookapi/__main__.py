"""Run the book API with ``python -m bookapi``."""

import argparse
import os

from .app import create_app, make_threaded_server


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m bookapi", description=__doc__)
    parser.add_argument(
        "--host",
        default=os.environ.get("BOOKAPI_HOST", "127.0.0.1"),
        help="address to bind (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("BOOKAPI_PORT", "8000"),
        help="port to listen on (default: %(default)s)",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("BOOKAPI_DB", "books.db"),
        help="path to the SQLite database file (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    app = create_app(args.db)
    with make_threaded_server(args.host, args.port, app) as server:
        host, port = server.server_address[:2]
        print(f"Book API listening on http://{host}:{port} (database: {args.db})", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            app.store.close()


if __name__ == "__main__":
    main()
