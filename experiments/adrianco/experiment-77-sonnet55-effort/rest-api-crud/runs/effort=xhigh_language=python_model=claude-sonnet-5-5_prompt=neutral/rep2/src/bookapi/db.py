"""SQLite-backed storage for books."""

from __future__ import annotations

import sqlite3
import threading
from typing import Any

# SQLite's INTEGER PRIMARY KEY is a signed 64-bit value.
_MAX_ID = 2**63 - 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author);
"""

# Column names that may appear in an UPDATE. Only these are ever interpolated
# into SQL; values always go through parameters.
_UPDATABLE = ("title", "author", "year", "isbn")


def _casefold(value: str | None) -> str | None:
    # SQLite's built-in LOWER()/NOCASE only handle ASCII.
    return value.casefold() if value is not None else None


def _is_valid_id(book_id: int) -> bool:
    # Out-of-range ids cannot exist, and binding them would raise OverflowError.
    return 0 < book_id <= _MAX_ID


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class BookStore:
    """Thread-safe book repository on a single SQLite connection."""

    def __init__(self, path: str = "books.db") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.create_function("casefold", 1, _casefold, deterministic=True)
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def ping(self) -> None:
        """Raise if the database is not usable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, title: str, author: str, year: int | None, isbn: str | None) -> dict[str, Any]:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
            return self._fetch(cur.lastrowid)  # type: ignore[return-value]

    def list_books(self, author: str | None = None) -> list[dict[str, Any]]:
        """All books ordered by id, optionally filtered by exact (case-insensitive) author."""
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE casefold(author) = ? ORDER BY id",
                    (author.strip().casefold(),),
                ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._lock:
            return self._fetch(book_id)

    def update(self, book_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        """Apply ``fields`` to a book. Returns the new row, or None if it does not exist."""
        if not _is_valid_id(book_id):
            return None
        columns = [c for c in _UPDATABLE if c in fields]
        with self._lock, self._conn:
            if columns:
                assignments = ", ".join(f"{c} = ?" for c in columns)
                params = [fields[c] for c in columns] + [book_id]
                cur = self._conn.execute(f"UPDATE books SET {assignments} WHERE id = ?", params)
                if cur.rowcount == 0:
                    return None
            return self._fetch(book_id)

    def delete(self, book_id: int) -> bool:
        if not _is_valid_id(book_id):
            return False
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def _fetch(self, book_id: int) -> dict[str, Any] | None:
        if not _is_valid_id(book_id):
            return None
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_dict(row) if row else None
