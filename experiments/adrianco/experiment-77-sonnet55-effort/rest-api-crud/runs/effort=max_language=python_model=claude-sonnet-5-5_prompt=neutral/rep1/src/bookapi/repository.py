"""SQLite-backed storage for books."""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any

from .models import Book, BookData

DEFAULT_DATABASE = "books.db"

# Largest value of an SQLite INTEGER PRIMARY KEY. Bigger ids cannot exist (and binding
# one as a parameter raises OverflowError), so they are treated as "not found".
MAX_ID = 2**63 - 1

_COLUMNS = "id, title, author, year, isbn"

# AUTOINCREMENT guarantees an id is never handed out twice, even after its book is deleted.
# The CHECKs are a safety net; the API validates before anything reaches the database.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL CHECK (length(trim(title)) > 0),
    author TEXT NOT NULL CHECK (length(trim(author)) > 0),
    year   INTEGER,
    isbn   TEXT
);
"""


def _casefold(value: str | None) -> str | None:
    """SQL function backing case-insensitive comparisons (Unicode-aware, unlike NOCASE)."""
    return None if value is None else value.casefold()


def _to_book(row: sqlite3.Row) -> Book:
    return Book(row["id"], row["title"], row["author"], row["year"], row["isbn"])


def _storable_id(book_id: Any) -> bool:
    return isinstance(book_id, int) and 0 < book_id <= MAX_ID


class BookRepository:
    """Thread-safe CRUD access to the ``books`` table.

    One connection is shared by every thread and guarded by a lock. That keeps
    ``":memory:"`` databases working (each connection would otherwise get its own empty
    database) and costs nothing in practice, as SQLite serialises writers anyway.
    """

    def __init__(self, database: str | os.PathLike[str] = DEFAULT_DATABASE) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(os.fspath(database), check_same_thread=False)
        try:
            self._conn.row_factory = sqlite3.Row
            self._conn.create_function("casefold", 1, _casefold, deterministic=True)
            with self._conn:
                self._conn.executescript(_SCHEMA)
        except BaseException:
            self._conn.close()
            raise

    def create(self, data: BookData) -> Book:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data.title, data.author, data.year, data.isbn),
            )
        book_id = cursor.lastrowid
        assert book_id is not None  # always set after a successful INSERT
        return Book(book_id, data.title, data.author, data.year, data.isbn)

    def get(self, book_id: int) -> Book | None:
        if not _storable_id(book_id):
            return None
        with self._lock:
            row = self._conn.execute(
                f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return None if row is None else _to_book(row)

    def list_books(self, author: str | None = None) -> list[Book]:
        """All books ordered by id; ``author`` keeps only exact, case-insensitive matches."""
        sql = f"SELECT {_COLUMNS} FROM books"
        params: tuple[str, ...] = ()
        if author is not None:
            sql += " WHERE casefold(author) = ?"
            params = (author.casefold(),)
        with self._lock:
            rows = self._conn.execute(sql + " ORDER BY id", params).fetchall()
        return [_to_book(row) for row in rows]

    def update(self, book_id: int, data: BookData) -> Book | None:
        """Replace every field of a book; returns ``None`` if it does not exist."""
        if not _storable_id(book_id):
            return None
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data.title, data.author, data.year, data.isbn, book_id),
            )
        if cursor.rowcount == 0:
            return None
        return Book(book_id, data.title, data.author, data.year, data.isbn)

    def delete(self, book_id: int) -> bool:
        """Delete a book; returns whether it existed."""
        if not _storable_id(book_id):
            return False
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0

    def ping(self) -> None:
        """Raise ``sqlite3.Error`` if the database is not usable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> BookRepository:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
