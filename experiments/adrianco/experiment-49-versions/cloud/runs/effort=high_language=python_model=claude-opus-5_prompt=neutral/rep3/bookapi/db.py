"""SQLite persistence helpers.

One connection is opened per Flask application context and closed when the
context tears down, which keeps each request on its own connection without
paying the cost of opening one per query.
"""

from __future__ import annotations

import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    author     TEXT NOT NULL,
    year       INTEGER,
    isbn       TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


def get_db() -> sqlite3.Connection:
    """Return the connection bound to the current application context."""
    if "db" not in g:
        connection = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_exception: BaseException | None = None) -> None:
    """Close the application-context connection, if one was opened."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db(app) -> None:
    """Create the schema if it does not exist yet."""
    with app.app_context():
        get_db().executescript(SCHEMA)
