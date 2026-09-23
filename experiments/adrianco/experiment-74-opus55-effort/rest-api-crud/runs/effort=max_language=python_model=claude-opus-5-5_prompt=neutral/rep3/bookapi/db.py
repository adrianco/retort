"""SQLite connection handling and schema creation."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g

# AUTOINCREMENT stops SQLite from reusing the ID of a deleted book, so a stale
# /books/{id} URL can never start pointing at a different book.
SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL CHECK (trim(title) <> ''),
    author TEXT    NOT NULL CHECK (trim(author) <> ''),
    year   INTEGER,
    isbn   TEXT
);
"""


def connect(path: str) -> sqlite3.Connection:
    """Open *path* with dict-like rows and a Unicode-aware ``casefold()`` SQL function."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # SQLite's lower() and NOCASE only fold ASCII letters; str.casefold handles
    # all of Unicode, so "GARCÍA" matches "García".
    conn.create_function("casefold", 1, _casefold, deterministic=True)
    return conn


def _casefold(value: Any) -> Any:
    return value.casefold() if isinstance(value, str) else value


def get_db() -> sqlite3.Connection:
    """The connection for the current request, opened on first use."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exception: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app: Flask) -> None:
    """Create the database and schema if needed, and close connections after each request."""
    path = app.config["DATABASE"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as conn:
        conn.executescript(SCHEMA)
    app.teardown_appcontext(close_db)
