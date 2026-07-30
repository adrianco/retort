"""SQLite persistence for the book collection.

A connection is opened lazily per request and closed when the application
context tears down, which keeps SQLite's "one connection per thread" rule
satisfied without a connection pool.
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
    isbn       TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Partial index so many books may have no ISBN, but a given ISBN is unique.
CREATE UNIQUE INDEX IF NOT EXISTS ux_books_isbn
    ON books (isbn) WHERE isbn IS NOT NULL;
"""


def get_db() -> sqlite3.Connection:
    """Return the connection bound to the current application context."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        # Enforce foreign keys and pick a journal mode that tolerates
        # concurrent readers alongside a writer.
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


def close_db(exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create tables and indexes if they do not already exist."""
    get_db().executescript(SCHEMA)
    get_db().commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
