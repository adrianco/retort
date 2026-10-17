"""SQLite storage for the book collection."""

from __future__ import annotations

import sqlite3
import threading
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

_COLUMNS = "id, title, author, year, isbn"


def _casefold(value: str | None) -> str | None:
    # SQLite's lower() only folds ASCII, so register a Unicode-aware version.
    return None if value is None else value.casefold()


class BookRepository:
    """Persists books in SQLite.

    One connection is shared by all request threads, so every operation holds
    a lock. Pass ":memory:" for a throwaway database.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.create_function("casefold", 1, _casefold, deterministic=True)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    def create(self, book: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            self._conn.commit()
            return self._fetch(cursor.lastrowid)

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._lock:
            return self._fetch(book_id)

    def search(self, author: str | None = None) -> list[dict[str, Any]]:
        """Return books ordered by id. If `author` is given, keep books whose
        author contains it, ignoring case."""
        sql = f"SELECT {_COLUMNS} FROM books"
        params: tuple[str, ...] = ()
        if author is not None:
            sql += " WHERE instr(casefold(author), ?) > 0"
            params = (author.casefold(),)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def update(self, book_id: int, book: dict[str, Any]) -> dict[str, Any] | None:
        """Overwrite every field of a book. Returns None if it does not exist."""
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            self._conn.commit()
            if cursor.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete(self, book_id: int) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cursor.rowcount > 0

    def ping(self) -> bool:
        try:
            with self._lock:
                self._conn.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _fetch(self, book_id: int) -> dict[str, Any] | None:
        # Caller must hold self._lock.
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row is not None else None
