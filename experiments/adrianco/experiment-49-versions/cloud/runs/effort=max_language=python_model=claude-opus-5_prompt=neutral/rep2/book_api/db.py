"""SQLite connection management.

For a file database one connection is opened per request and closed when the
application context tears down, which keeps the service safe under the threaded
development server and under WSGI servers such as gunicorn or waitress.

An in-memory database is different: SQLite's shared cache locks whole tables
and answers a collision with ``SQLITE_LOCKED``, which the busy handler never
retries.  Concurrent connections would therefore fail instead of waiting, so
in-memory requests take turns on a single connection guarded by a lock.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from typing import Optional, Tuple

import click
from flask import Flask, current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    author          TEXT    NOT NULL CHECK (length(trim(author)) > 0),
    year            INTEGER,
    isbn            TEXT,
    isbn_normalized TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

-- An ISBN identifies an edition, so it may appear at most once.  The index is
-- partial so that any number of books may omit it.
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_normalized_unique
    ON books (isbn_normalized) WHERE isbn_normalized IS NOT NULL;

CREATE INDEX IF NOT EXISTS books_author_idx ON books (author COLLATE NOCASE);
"""


def _resolve_dsn(database: str) -> Tuple[str, bool]:
    """Map the configured database to a ``(dsn, uri_mode)`` pair.

    A plain ``:memory:`` database would be private to each connection, so it is
    translated into a uniquely named shared-cache URI.  Every connection of the
    application then sees the same in-memory database.
    """
    if database in (":memory:", "", None):
        return "file:book_api_{}?mode=memory&cache=shared".format(uuid.uuid4().hex), True
    return os.fspath(database), False


def _connect(dsn: str, uri_mode: bool, timeout: float, *, shared: bool = False) -> sqlite3.Connection:
    connection = sqlite3.connect(
        dsn, uri=uri_mode, timeout=timeout, check_same_thread=not shared
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if not uri_mode:
        # Write-ahead logging lets readers work while a writer holds the lock.
        # It is not available for in-memory databases.
        connection.execute("PRAGMA journal_mode = WAL")
    return connection


def _acquire_shared_connection() -> sqlite3.Connection:
    """Take the lock protecting the single in-memory connection."""
    state = current_app.extensions["book_api"]
    timeout = max(float(current_app.config["SQLITE_TIMEOUT"]), 1.0)
    if not state["lock"].acquire(timeout=timeout):
        raise sqlite3.OperationalError("timed out waiting for the in-memory database")
    g.sqlite_lock = state["lock"]
    return state["keeper_connection"]


def get_db() -> sqlite3.Connection:
    """Return the connection bound to the current application context."""
    if "sqlite_db" not in g:
        if current_app.config["DATABASE_URI_MODE"]:
            g.sqlite_db = _acquire_shared_connection()
        else:
            g.sqlite_db = _connect(
                current_app.config["DATABASE_DSN"],
                False,
                current_app.config["SQLITE_TIMEOUT"],
            )
    return g.sqlite_db


def close_db(exception: Optional[BaseException] = None) -> None:
    """Release the connection bound to the application context that is ending."""
    connection = g.pop("sqlite_db", None)
    lock = g.pop("sqlite_lock", None)
    if lock is None:
        if connection is not None:
            connection.close()
        return
    try:
        if connection is not None:
            # The shared connection outlives the request, so it must never be
            # handed on with a transaction left open.
            connection.rollback()
    finally:
        lock.release()


def init_db() -> None:
    """Create the schema if it is not there yet (safe to call repeatedly)."""
    connection = get_db()
    connection.executescript(SCHEMA)
    connection.commit()


@click.command("init-db")
def init_db_command() -> None:  # pragma: no cover - thin CLI wrapper
    """Flask CLI command: ``flask --app wsgi init-db``."""
    init_db()
    click.echo("Initialised the database at {}.".format(current_app.config["DATABASE"]))


def init_app(app: Flask) -> None:
    """Wire connection handling into ``app`` and make sure the schema exists."""
    dsn, uri_mode = _resolve_dsn(app.config["DATABASE"])
    app.config["DATABASE_DSN"] = dsn
    app.config["DATABASE_URI_MODE"] = uri_mode

    if not uri_mode:
        directory = os.path.dirname(os.path.abspath(dsn))
        os.makedirs(directory, exist_ok=True)

    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    if uri_mode:
        # A shared-cache in-memory database only lives as long as at least one
        # connection to it is open, so the app keeps one for its whole lifetime
        # and every request borrows it under the lock.
        keeper = _connect(dsn, True, app.config["SQLITE_TIMEOUT"], shared=True)
        app.extensions.setdefault("book_api", {}).update(
            keeper_connection=keeper, lock=threading.RLock()
        )

    with app.app_context():
        init_db()
