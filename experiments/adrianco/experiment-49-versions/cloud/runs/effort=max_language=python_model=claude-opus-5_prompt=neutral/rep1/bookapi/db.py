"""SQLite connection management and schema bootstrapping."""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

from flask import Flask, current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    author     TEXT    NOT NULL CHECK (length(trim(author)) > 0),
    year       INTEGER CHECK (year IS NULL OR (year BETWEEN 1 AND 9999)),
    isbn       TEXT,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


def connect(database: str) -> sqlite3.Connection:
    """Open a configured connection to ``database``."""
    if database != ":memory:":
        parent = os.path.dirname(os.path.abspath(database))
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    # Enforce CHECK/NOT NULL semantics predictably and keep readers from
    # blocking writers.
    conn.execute("PRAGMA foreign_keys = ON")
    if database != ":memory:":
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:  # pragma: no cover - filesystem dependent
            pass
    return conn


def get_db() -> sqlite3.Connection:
    """Return the connection bound to the current request, opening it lazily."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc: Optional[BaseException] = None) -> None:
    """Close the request-scoped connection, if one was opened."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app: Flask) -> None:
    """Create the schema if it does not exist yet."""
    conn = connect(app.config["DATABASE"])
    try:
        with conn:
            conn.executescript(SCHEMA)
    finally:
        conn.close()


def init_app(app: Flask) -> None:
    """Wire connection handling into the application lifecycle."""
    app.teardown_appcontext(close_db)
    init_db(app)
