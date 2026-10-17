"""Command-line entry point: ``python -m bookapi``."""

import argparse
import logging
import os

from .http_app import create_server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("BOOKAPI_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOOKAPI_PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("BOOKAPI_DB", "books.db"))
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(message)s")
    server = create_server(args.host, args.port, args.db)
    logging.info("serving on http://%s:%d (db=%s)", *server.server_address[:2], args.db)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
