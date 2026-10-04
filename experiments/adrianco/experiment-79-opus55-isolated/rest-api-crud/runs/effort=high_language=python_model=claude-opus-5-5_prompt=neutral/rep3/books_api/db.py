"""SQLite persistence for books."""

from __future__ import annotations

import sqlite3
import threading
from typing import Any, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""

_COLUMNS = "id, title, author, year, isbn"

# SQLite INTEGER columns are signed 64-bit; larger ids cannot exist.
_MAX_ID = 2**63 - 1

Book = dict[str, Any]


class BookRepository:
    """CRUD access to the ``books`` table.

    A single connection is shared between threads and guarded by a lock, which
    keeps ``:memory:`` databases usable from a threaded server.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def ping(self) -> None:
        """Raise ``sqlite3.Error`` if the database is not usable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, fields: Book) -> Book:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) "
                "VALUES (:title, :author, :year, :isbn)",
                fields,
            )
            return self._fetch(cursor.lastrowid)

    def list_books(self, author: Optional[str] = None) -> list[Book]:
        query = f"SELECT {_COLUMNS} FROM books"
        params: tuple[Any, ...] = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get(self, book_id: int) -> Optional[Book]:
        if book_id > _MAX_ID:
            return None
        with self._lock:
            return self._fetch(book_id)

    def update(self, book_id: int, fields: Book) -> Optional[Book]:
        """Replace every field of a book; return ``None`` if it does not exist."""
        if book_id > _MAX_ID:
            return None
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = :title, author = :author, "
                "year = :year, isbn = :isbn WHERE id = :id",
                {**fields, "id": book_id},
            )
            if cursor.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete(self, book_id: int) -> bool:
        if book_id > _MAX_ID:
            return False
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    def _fetch(self, book_id: Optional[int]) -> Optional[Book]:
        # Caller must hold the lock.
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row is not None else None
