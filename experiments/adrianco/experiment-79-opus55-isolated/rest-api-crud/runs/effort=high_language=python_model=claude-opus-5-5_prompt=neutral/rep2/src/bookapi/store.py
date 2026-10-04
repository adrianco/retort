"""SQLite persistence for books."""

import sqlite3
import threading
from typing import Any

# SQLite integer primary keys are signed 64-bit; larger ids cannot exist.
MAX_ID = 2**63 - 1

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


class BookStore:
    """Book repository on a single SQLite connection.

    The connection is shared between request threads and guarded by a lock.
    SQLite serialises writers anyway, and one connection keeps ``:memory:``
    databases working (each new connection would otherwise see an empty DB).
    """

    def __init__(self, path: str = "books.db") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
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

    def create(self, book: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) "
                "VALUES (:title, :author, :year, :isbn)",
                book,
            )
            return self._get(cursor.lastrowid)

    def list(self, author: str | None = None) -> list[dict[str, Any]]:
        query = f"SELECT {_COLUMNS} FROM books"
        params: tuple[Any, ...] = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            return [dict(row) for row in self._conn.execute(query, params)]

    def get(self, book_id: int) -> dict[str, Any] | None:
        if not _valid_id(book_id):
            return None
        with self._lock:
            return self._get(book_id)

    def update(self, book_id: int, book: dict[str, Any]) -> dict[str, Any] | None:
        """Replace a book's fields. Returns ``None`` if it does not exist."""
        if not _valid_id(book_id):
            return None
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = :title, author = :author, "
                "year = :year, isbn = :isbn WHERE id = :id",
                {**book, "id": book_id},
            )
            if cursor.rowcount == 0:
                return None
            return self._get(book_id)

    def delete(self, book_id: int) -> bool:
        """Delete a book. Returns ``False`` if it does not exist."""
        if not _valid_id(book_id):
            return False
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    def _get(self, book_id: int | None) -> dict[str, Any] | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row is not None else None


def _valid_id(book_id: int) -> bool:
    return 0 < book_id <= MAX_ID
