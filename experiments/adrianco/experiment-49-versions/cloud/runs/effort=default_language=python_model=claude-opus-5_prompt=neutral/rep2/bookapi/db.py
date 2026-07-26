"""SQLite connection handling and schema management."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    year       INTEGER,
    isbn       TEXT    UNIQUE,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


def resolve_db_path(db_path: str | os.PathLike[str] | None = None) -> str:
    """Pick the database file: explicit argument, then $BOOKS_DB_PATH, then default."""
    if db_path is not None:
        return str(db_path)
    return os.environ.get("BOOKS_DB_PATH") or DEFAULT_DB_PATH


def connect(db_path: str | os.PathLike[str]) -> sqlite3.Connection:
    """Open a connection with the conventions the rest of the app expects."""
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Concurrent readers alongside a writer; harmless for a single-process server.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: str | os.PathLike[str]) -> None:
    """Create the schema if it does not exist yet."""
    parent = Path(db_path).expanduser().parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
