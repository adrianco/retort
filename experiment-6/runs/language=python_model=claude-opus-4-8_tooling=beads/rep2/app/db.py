"""SQLite storage layer for the book collection service."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "books.db"

# Module-level path so tests can point the app at a temporary database.
_db_path = str(DEFAULT_DB_PATH)


def set_db_path(path: str) -> None:
    """Override the database file location (used by tests)."""
    global _db_path
    _db_path = str(path)


def get_db_path() -> str:
    return _db_path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_connection():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the books table if it does not already exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                title   TEXT NOT NULL,
                author  TEXT NOT NULL,
                year    INTEGER,
                isbn    TEXT
            )
            """
        )
