"""SQLite-backed storage for books."""

from __future__ import annotations

import os
import sqlite3
import threading

from .models import Book, BookData

# Largest value SQLite can store in an INTEGER column. Ids outside the range
# cannot exist, and passing them to sqlite3 would raise OverflowError.
_MAX_SQLITE_INT = 2**63 - 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    author TEXT    NOT NULL CHECK (length(trim(author)) > 0),
    year   INTEGER,
    isbn   TEXT
)
"""

_COLUMNS = "id, title, author, year, isbn"


def _casefold(value: str | None) -> str | None:
    return value.casefold() if value is not None else None


class BookRepository:
    """CRUD operations on the ``books`` table.

    One connection is shared by all threads and access is serialised with a
    lock, which keeps things simple and also makes ``":memory:"`` databases
    work with a multi-threaded server. AUTOINCREMENT guarantees ids are never
    reused, so a URL of a deleted book never starts pointing at another one.
    """

    def __init__(self, database: str | os.PathLike[str] = ":memory:") -> None:
        self._conn = sqlite3.connect(database, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # SQLite's lower()/LIKE only fold ASCII; use Python's Unicode casefold.
        self._conn.create_function("casefold", 1, _casefold, deterministic=True)
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(_SCHEMA)

    def create(self, data: BookData) -> Book:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data.title, data.author, data.year, data.isbn),
            )
            book_id = cursor.lastrowid
        assert book_id is not None
        return Book(id=book_id, title=data.title, author=data.author, year=data.year, isbn=data.isbn)

    def list_books(self, author: str | None = None) -> list[Book]:
        """Return all books ordered by id.

        ``author`` filters to books whose author contains it, ignoring case.
        """
        query = f"SELECT {_COLUMNS} FROM books"
        params: tuple[str, ...] = ()
        if author:
            query += " WHERE instr(casefold(author), ?) > 0"
            params = (author.casefold(),)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [_to_book(row) for row in rows]

    def get(self, book_id: int) -> Book | None:
        if not _is_valid_id(book_id):
            return None
        with self._lock:
            row = self._conn.execute(
                f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return _to_book(row) if row is not None else None

    def update(self, book_id: int, data: BookData) -> Book | None:
        """Replace all fields of a book; returns None if it does not exist."""
        if not _is_valid_id(book_id):
            return None
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data.title, data.author, data.year, data.isbn, book_id),
            )
        if cursor.rowcount == 0:
            return None
        return Book(id=book_id, title=data.title, author=data.author, year=data.year, isbn=data.isbn)

    def delete(self, book_id: int) -> bool:
        """Delete a book; returns False if it did not exist."""
        if not _is_valid_id(book_id):
            return False
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0

    def ping(self) -> bool:
        """Return True if the database answers a trivial query."""
        try:
            with self._lock:
                self._conn.execute("SELECT 1 FROM books LIMIT 1").fetchall()
        except sqlite3.Error:
            return False
        return True

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _is_valid_id(book_id: int) -> bool:
    return 0 < book_id <= _MAX_SQLITE_INT


def _to_book(row: sqlite3.Row) -> Book:
    return Book(
        id=row["id"],
        title=row["title"],
        author=row["author"],
        year=row["year"],
        isbn=row["isbn"],
    )
