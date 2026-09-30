"""SQLite-backed storage for books."""

from __future__ import annotations

import os
import sqlite3
import threading
import unicodedata
from typing import cast

from .models import Book, BookInput

# Ids are SQLite INTEGERs (signed 64-bit). A larger value can never match a row and
# would make the driver raise OverflowError instead of simply finding nothing.
_MAX_ID = 2**63 - 1

_COLUMNS = "id, title, author, year, isbn"

# AUTOINCREMENT guarantees the id of a deleted book is never handed out again.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""


def _fold(text: str) -> str:
    """Comparison key that ignores case and how accents are composed.

    This is the Unicode standard's canonical caseless matching (D145): "É", "é" and
    "e" plus a combining acute accent all fold to the same key. SQLite's own
    NOCASE/lower() only understand ASCII.
    """
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", text).casefold())


def _sql_fold(value: object) -> str | None:
    return _fold(value) if isinstance(value, str) else None


def _is_possible_id(book_id: int) -> bool:
    return 0 < book_id <= _MAX_ID


class BookRepository:
    """Create, read, update and delete books in a SQLite database.

    One connection is shared by all threads and guarded by a lock. That keeps
    ``":memory:"`` databases usable from a threaded server, and SQLite serialises
    writers anyway. The connection is in autocommit mode: every method issues a
    single statement, which is atomic on its own.
    """

    def __init__(self, database: str | os.PathLike[str] = ":memory:") -> None:
        if not os.fspath(database):
            # SQLite would quietly open an anonymous temporary database that is
            # discarded on exit: every "saved" book would vanish.
            raise ValueError("database path must not be empty (use ':memory:' for a throwaway one)")
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(database, check_same_thread=False, isolation_level=None)
        try:
            self._conn.create_function("fold", 1, _sql_fold, deterministic=True)
            self._conn.execute(_SCHEMA)
        except sqlite3.Error:
            self._conn.close()
            raise

    def create(self, data: BookInput) -> Book:
        """Store a new book and return it with its generated id."""
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data.title, data.author, data.year, data.isbn),
            )
        book_id = cast(int, cursor.lastrowid)  # always set after a successful INSERT
        return Book(book_id, data.title, data.author, data.year, data.isbn)

    def get(self, book_id: int) -> Book | None:
        """Return the book with this id, or ``None``."""
        if not _is_possible_id(book_id):
            return None
        with self._lock:
            row = self._conn.execute(
                f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return Book(*row) if row else None

    def list_books(self, author: str | None = None) -> list[Book]:
        """Return all books in id order, optionally only those by ``author``.

        The author is matched in full but ignoring case and accent composition
        (``"tolkien"`` finds ``"Tolkien"``, not ``"J.R.R. Tolkien"``).
        """
        query = f"SELECT {_COLUMNS} FROM books"
        params: tuple[str, ...] = ()
        if author is not None:
            key = _fold(author)
            try:
                key.encode("utf-8")
            except UnicodeEncodeError:
                return []  # text SQLite cannot store (a lone surrogate) matches nothing
            query += " WHERE fold(author) = ?"
            params = (key,)
        with self._lock:
            rows = self._conn.execute(query + " ORDER BY id", params).fetchall()
        return [Book(*row) for row in rows]

    def update(self, book_id: int, data: BookInput) -> Book | None:
        """Replace every field of a book. Returns the new state, or ``None`` if absent."""
        if not _is_possible_id(book_id):
            return None
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data.title, data.author, data.year, data.isbn, book_id),
            )
        if cursor.rowcount == 0:
            return None
        return Book(book_id, data.title, data.author, data.year, data.isbn)

    def delete(self, book_id: int) -> bool:
        """Delete a book. Returns whether it existed."""
        if not _is_possible_id(book_id):
            return False
        with self._lock:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0

    def ping(self) -> None:
        """Raise ``sqlite3.Error`` unless the database can be queried."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def close(self) -> None:
        """Close the connection. Closing twice is harmless."""
        with self._lock:
            self._conn.close()
