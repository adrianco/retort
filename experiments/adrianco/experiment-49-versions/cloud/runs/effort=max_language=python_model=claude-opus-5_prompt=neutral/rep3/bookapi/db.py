"""SQLite connection management and schema setup.

One connection is opened lazily per request and closed when the application
context tears down, which keeps ``sqlite3``'s single-thread-per-connection rule
satisfied without any global state.
"""

from __future__ import annotations

import os
import sqlite3

from flask import Flask, current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
);

-- An ISBN identifies an edition, so it must be unique when supplied. SQLite
-- treats NULLs as distinct, and the partial index makes that intent explicit:
-- any number of books may omit an ISBN.
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique
    ON books (isbn) WHERE isbn IS NOT NULL;

-- Supports the ?author= filter, which compares case-insensitively.
CREATE INDEX IF NOT EXISTS books_author_idx ON books (author COLLATE NOCASE);
"""


def get_db() -> sqlite3.Connection:
    """Return this request's connection, opening it on first use."""
    if "db" not in g:
        connection = sqlite3.connect(
            current_app.config["DATABASE"],
            timeout=current_app.config["DATABASE_TIMEOUT"],
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(exception: BaseException | None = None) -> None:
    """Close the request's connection, if one was opened."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db(app: Flask) -> None:
    """Create the schema if it does not exist yet. Safe to run repeatedly."""
    database = app.config["DATABASE"]
    directory = os.path.dirname(os.path.abspath(database))
    if database != ":memory:":
        os.makedirs(directory, exist_ok=True)

    connection = sqlite3.connect(database, timeout=app.config["DATABASE_TIMEOUT"])
    try:
        if database != ":memory:":
            # WAL lets readers proceed while a writer holds the write lock.
            connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def init_app(app: Flask) -> None:
    """Wire connection teardown into the app and ensure the schema exists."""
    app.teardown_appcontext(close_db)
    init_db(app)
