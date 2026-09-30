"""SQLite-backed persistence for books."""

from __future__ import annotations

import sqlite3
import threading
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

# SQLite's built-in NOCASE only folds ASCII; casefold handles the rest of Unicode.
_CASEFOLD = "CASEFOLD"

SQLITE_MAX_INT = 2**63 - 1


def _casefold_collation(a: str, b: str) -> int:
    a, b = a.casefold(), b.casefold()
    return (a > b) - (a < b)


class BookStore:
    """Thread-safe book repository over a single SQLite connection.

    ``path`` may be a file path or ``":memory:"``. One shared connection guarded
    by a lock keeps in-memory databases usable from every request thread.
    """

    def __init__(self, path: str = "books.db") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.create_collation(_CASEFOLD, _casefold_collation)
        with self._lock, self._conn:
            self._conn.execute(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def ping(self) -> None:
        """Raise ``sqlite3.Error`` if the database is not usable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, book: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            return self._fetch(cursor.lastrowid)  # type: ignore[return-value]

    def list_books(self, author: str | None = None) -> list[dict[str, Any]]:
        """Return all books ordered by id, optionally filtered by exact
        (case-insensitive) author name."""
        sql = "SELECT id, title, author, year, isbn FROM books"
        params: tuple[Any, ...] = ()
        if author is not None:
            sql += f" WHERE author = ? COLLATE {_CASEFOLD}"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            return [dict(row) for row in self._conn.execute(sql, params)]

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._lock:
            return self._fetch(book_id)

    def update(self, book_id: int, book: dict[str, Any]) -> dict[str, Any] | None:
        """Replace all fields of a book; return it, or ``None`` if it does not exist."""
        if not self._in_range(book_id):
            return None
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            if cursor.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete(self, book_id: int) -> bool:
        if not self._in_range(book_id):
            return False
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    def _fetch(self, book_id: int) -> dict[str, Any] | None:
        # Caller must hold the lock.
        if not self._in_range(book_id):
            return None
        row = self._conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _in_range(book_id: int) -> bool:
        # Ids beyond 64 bits cannot exist and would make sqlite3 raise OverflowError.
        return 0 <= book_id <= SQLITE_MAX_INT
