"""SQLite connection management and schema bootstrapping.

One connection is opened per request and closed when the request context tears
down, which keeps each connection confined to the thread that uses it.  That is
the pattern SQLite is happiest with under a threaded WSGI server.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from typing import Any

from flask import Flask, current_app, g

#: Seconds a writer will wait for a competing writer before giving up.
BUSY_TIMEOUT_SECONDS = 5.0

#: Characters the blank-check below strips: space, tab, LF, CR.  Spelled with
#: char() because SQLite's one-argument trim() removes spaces only.
_BLANKS = "' ' || char(9) || char(10) || char(13)"

SCHEMA = f"""
-- The blank checks are fussier than they look: length() rather than <> '' because
-- length() stops at the first NUL, so it also rejects a NUL-only string that the
-- comparison would call non-empty.
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL CHECK (length(trim(title,  {_BLANKS})) > 0),
    author     TEXT    NOT NULL CHECK (length(trim(author, {_BLANKS})) > 0),
    year       INTEGER,
    isbn       TEXT,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_books_title  ON books (title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_books_year   ON books (year);
"""

_KEEPALIVE_KEY = "bookapi_memory_keepalive"


def _is_memory(database: str) -> bool:
    return database == ":memory:"


def _dsn(app: Flask) -> tuple[str, bool]:
    """Return the ``(dsn, use_uri)`` pair used to open a connection.

    A plain ``:memory:`` database would give every connection its own private,
    empty database.  Mapping it to a named shared-cache URI instead lets the
    per-request connections of a single app instance see the same data, which
    makes ``DATABASE=":memory:"`` usable for tests and demos.
    """
    database = app.config["DATABASE"]
    if _is_memory(database):
        return f"file:{app.config['MEMORY_DB_NAME']}?mode=memory&cache=shared", True
    return database, False


def connect(app: Flask) -> sqlite3.Connection:
    """Open a fresh, fully configured connection to the app's database."""
    dsn, use_uri = _dsn(app)
    connection = sqlite3.connect(
        dsn,
        uri=use_uri,
        timeout=BUSY_TIMEOUT_SECONDS,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {int(BUSY_TIMEOUT_SECONDS * 1000)}")
    if not _is_memory(app.config["DATABASE"]):
        # WAL lets readers proceed while a writer holds the database.
        connection.execute("PRAGMA journal_mode = WAL")
    return connection


def get_db() -> sqlite3.Connection:
    """Return this request's connection, opening one on first use."""
    if "db" not in g:
        g.db = connect(current_app)
    return g.db


def close_db(_exception: BaseException | None = None) -> None:
    """Close the request-scoped connection, if one was opened."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db(app: Flask) -> None:
    """Create the schema if it is not there yet."""
    if _is_memory(app.config["DATABASE"]):
        # Hold one connection open for the lifetime of the app: a shared-cache
        # in-memory database is destroyed as soon as its last connection closes.
        keepalive = connect(app)
        app.extensions[_KEEPALIVE_KEY] = keepalive
        keepalive.executescript(SCHEMA)
        keepalive.commit()
        return

    directory = os.path.dirname(os.path.abspath(app.config["DATABASE"]))
    os.makedirs(directory, exist_ok=True)
    connection = connect(app)
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def init_app(app: Flask) -> None:
    """Wire database lifecycle management into the application."""
    app.config.setdefault("MEMORY_DB_NAME", f"bookapi-{uuid.uuid4().hex}")
    app.teardown_appcontext(close_db)
    init_db(app)


def ping(connection: sqlite3.Connection) -> dict[str, Any]:
    """Cheap liveness probe that also proves the schema is in place."""
    row = connection.execute("SELECT COUNT(*) AS total FROM books").fetchone()
    return {"books": row["total"]}
