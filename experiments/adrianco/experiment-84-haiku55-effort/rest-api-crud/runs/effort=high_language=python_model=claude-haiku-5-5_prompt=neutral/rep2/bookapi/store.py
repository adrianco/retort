"""SQLite persistence for books."""

from __future__ import annotations

import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


class BookStore:
    """Stores books in a SQLite database.

    A single connection is shared by all threads and guarded by a lock. This keeps
    ":memory:" databases working and serialises writes from the threaded server.
    """

    def __init__(self, path: str = "books.db") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def ping(self) -> None:
        """Raise sqlite3.Error if the database is unreachable."""
        with self._lock:
            self._conn.execute("SELECT 1")

    def create(self, book: dict[str, object]) -> dict[str, object]:
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn)"
                " VALUES (:title, :author, :year, :isbn)",
                book,
            )
            self._conn.commit()
            return self._fetch(cursor.lastrowid)

    def get(self, book_id: int) -> dict[str, object] | None:
        with self._lock:
            return self._fetch(book_id)

    def list_books(self, author: str | None = None) -> list[dict[str, object]]:
        """List books in insertion order. `author` is an exact, case-insensitive match."""
        sql = "SELECT * FROM books"
        params: tuple[str, ...] = ()
        if author is not None:
            sql += " WHERE author COLLATE NOCASE = ?"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def update(self, book_id: int, book: dict[str, object]) -> dict[str, object] | None:
        """Replace every field of a book. Returns None if no such book exists."""
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE books SET title = :title, author = :author,"
                " year = :year, isbn = :isbn WHERE id = :id",
                {**book, "id": book_id},
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

    def _fetch(self, book_id: int) -> dict[str, object] | None:
        # Caller must hold self._lock.
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None
