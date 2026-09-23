"""Command-line entry point: ``python -m books_api``."""

import argparse
import os

import uvicorn

from books_api.app import DEFAULT_DB_PATH, create_app


def _env(name: str, default: str) -> str:
    # An empty variable counts as unset. An empty host in particular would
    # otherwise mean "listen on every interface".
    return os.environ.get(name) or default


def _host(text: str) -> str:
    if not text.strip():
        raise argparse.ArgumentTypeError("must not be empty (use 0.0.0.0 for every interface)")
    return text.strip()


def _port(text: str) -> int:
    try:
        port = int(text)
    except ValueError:
        port = -1
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"must be an integer from 1 to 65535, got {text!r}")
    return port


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the Books API.")
    # argparse applies ``type`` to string defaults too, so a bad environment
    # variable is reported as a usage error rather than a traceback.
    parser.add_argument(
        "--host",
        type=_host,
        default=_env("BOOKS_API_HOST", "127.0.0.1"),
        help="interface to listen on (env BOOKS_API_HOST, default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=_env("BOOKS_API_PORT", "8000"),
        help="port to listen on (env BOOKS_API_PORT, default: %(default)s)",
    )
    parser.add_argument(
        "--db",
        default=_env("BOOKS_API_DB", DEFAULT_DB_PATH),
        help="SQLite database file, created if missing (env BOOKS_API_DB, default: %(default)s)",
    )
    args = parser.parse_args(argv)
    try:
        app = create_app(args.db)
    except ValueError as exc:  # e.g. --db :memory:
        parser.error(f"argument --db: {exc}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
