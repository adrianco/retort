"""SQLite-backed storage for books."""

from __future__ import annotations

import os
import sqlite3
import threading
import unicodedata
from pathlib import Path
from typing import Optional, Union

from .validation import BookFields

DEFAULT_DATABASE = "books.db"

# SQLite integers are 64-bit; binding anything larger raises OverflowError.
_MAX_ID = 2**63 - 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL CHECK (length(trim(title)) > 0),
    author TEXT NOT NULL CHECK (length(trim(author)) > 0),
    year   INTEGER,
    isbn   TEXT
)
"""

_COLUMNS = "id, title, author, year, isbn"


class Book(BookFields):
    """A stored book: the editable fields plus the server-assigned ``id``."""

    id: int


def _fold(text: str) -> str:
    """Normalise ``text`` for case-insensitive comparison (SQLite's NOCASE only folds ASCII)."""
    return unicodedata.normalize("NFKC", text).casefold()


def _valid_id(book_id: int) -> bool:
    return 0 < book_id <= _MAX_ID


class BookRepository:
    """CRUD operations on the ``books`` table.

    A single connection is shared by all threads and guarded by a lock. That is
    plenty for SQLite (which serialises writers anyway) and it also makes
    ``":memory:"`` databases work, since each new connection to one would see
    its own empty database.
    """

    def __init__(self, database: Union[str, os.PathLike] = DEFAULT_DATABASE) -> None:
        path = os.fspath(database)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        try:
            self._conn.row_factory = sqlite3.Row
            self._conn.create_function("fold", 1, _fold, deterministic=True)
            self._conn.execute(_SCHEMA)  # also where a file that is not a database is detected
        except BaseException:
            self._conn.close()
            raise

    def create_book(self, fields: BookFields) -> Book:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (:title, :author, :year, :isbn)",
                fields,
            )
        return Book(id=cursor.lastrowid, **fields)

    def get_book(self, book_id: int) -> Optional[Book]:
        if not _valid_id(book_id):
            return None
        with self._lock:
            row = self._conn.execute(f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)).fetchone()
        return Book(**row) if row else None

    def list_books(self, author: Optional[str] = None) -> list[Book]:
        """All books in insertion order, optionally only those by ``author``.

        The author match is exact but ignores case (and Unicode normalisation).
        """
        query = f"SELECT {_COLUMNS} FROM books"
        params: tuple[str, ...] = ()
        if author is not None:
            query += " WHERE fold(author) = ?"
            params = (_fold(author),)
        with self._lock:
            rows = self._conn.execute(query + " ORDER BY id", params).fetchall()
        return [Book(**row) for row in rows]

    def update_book(self, book_id: int, fields: BookFields) -> Optional[Book]:
        """Replace every editable field of a book; ``None`` if there is no such book."""
        if not _valid_id(book_id):
            return None
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = :title, author = :author, year = :year, isbn = :isbn WHERE id = :id",
                {**fields, "id": book_id},
            )
        return Book(id=book_id, **fields) if cursor.rowcount else None

    def delete_book(self, book_id: int) -> bool:
        """Remove a book; ``False`` if there was no such book."""
        if not _valid_id(book_id):
            return False
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0

    def ping(self) -> None:
        """Raise :class:`sqlite3.Error` unless the ``books`` table can be read.

        (A bare ``SELECT 1`` would succeed even if the database file were gone or corrupt.)
        """
        with self._lock:
            self._conn.execute("SELECT 1 FROM books LIMIT 1").fetchone()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
