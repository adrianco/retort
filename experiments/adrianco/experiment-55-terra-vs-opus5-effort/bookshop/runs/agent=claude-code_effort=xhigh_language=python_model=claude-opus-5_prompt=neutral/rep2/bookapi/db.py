"""SQLite connection lifecycle and schema management."""

from __future__ import annotations

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

-- Matches the case-insensitive ?author= filter in list_books().
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


def connect(app: Flask) -> sqlite3.Connection:
    """Open a new connection to the app's database."""
    conn = sqlite3.connect(
        app.config["DATABASE"],
        timeout=app.config["DATABASE_TIMEOUT"],
    )
    conn.row_factory = sqlite3.Row
    return conn


def get_db() -> sqlite3.Connection:
    """Return the connection for the current request, opening it on demand."""
    if "db" not in g:
        g.db = connect(current_app)
    return g.db


def close_db(exc: BaseException | None = None) -> None:
    """Teardown hook: close the request's connection if one was opened."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app: Flask) -> None:
    """Create the schema if it does not exist yet."""
    conn = connect(app)
    try:
        if app.config["DATABASE"] != ":memory:":
            # Write-ahead logging lets readers run alongside a writer.
            conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
