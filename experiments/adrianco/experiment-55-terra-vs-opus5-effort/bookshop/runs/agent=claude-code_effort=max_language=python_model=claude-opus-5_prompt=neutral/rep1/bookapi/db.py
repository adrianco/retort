"""SQLite connection handling.

One connection per request, stashed on Flask's ``g`` and closed when the
application context tears down.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, current_app, g

MEMORY = ":memory:"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    year       INTEGER,
    -- UNIQUE still allows many NULLs in SQLite, so books without an ISBN
    -- coexist happily while real ISBNs stay unique.
    isbn       TEXT    UNIQUE,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


def _configure(conn: sqlite3.Connection, path: str) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    if path != MEMORY:
        # Write-ahead logging lets readers run while a write is in flight.
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def connect(path: str) -> sqlite3.Connection:
    """Open a configured connection to ``path``."""
    if path != MEMORY:
        parent = Path(path).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)
    return _configure(sqlite3.connect(path, timeout=5.0), path)


def get_db() -> sqlite3.Connection:
    """Return this request's connection, opening one on first use."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app: Flask) -> None:
    """Create the schema if it is not there yet."""
    conn = connect(app.config["DATABASE"])
    try:
        with conn:
            conn.executescript(SCHEMA)
    finally:
        conn.close()
