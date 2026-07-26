"""Run the development server: ``python -m book_api [--port 8000]``."""

from __future__ import annotations

import argparse
import os
from typing import Optional, Sequence

from . import create_app


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="book_api", description="Book collection REST API")
    parser.add_argument("--host", default=os.environ.get("BOOK_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOOK_API_PORT", "8000")))
    parser.add_argument(
        "--database",
        default=None,
        help="SQLite file to use, or ':memory:' for a throwaway database "
        "(default: $BOOK_API_DATABASE or books.db)",
    )
    parser.add_argument("--debug", action="store_true", help="enable the Flask reloader/debugger")
    args = parser.parse_args(argv)

    overrides = {"DATABASE": args.database} if args.database else None
    app = create_app(overrides)
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
