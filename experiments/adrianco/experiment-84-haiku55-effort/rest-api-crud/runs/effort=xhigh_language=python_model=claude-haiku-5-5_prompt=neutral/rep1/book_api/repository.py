"""SQLite-backed storage for books."""

import sqlite3
import threading
from dataclasses import asdict
from typing import Any

from .models import Book, BookFields

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


class BookRepository:
    """Stores books in a single SQLite connection.

    The connection is shared between request threads, so every operation holds
    a lock. Pass ``":memory:"`` for an ephemeral database (used by the tests).
    """

    def __init__(self, database: str = "books.db"):
        self._conn = sqlite3.connect(database, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def create(self, fields: BookFields) -> Book:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (fields.title, fields.author, fields.year, fields.isbn),
            )
            book_id = cursor.lastrowid
        return Book(id=book_id, **asdict(fields))

    def get(self, book_id: int) -> Book | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _to_book(row) if row else None

    def list_books(self, author: str | None = None) -> list[Book]:
        """Return all books in insertion order, optionally filtered by author.

        The author match is exact but ignores case (for ASCII letters, per SQLite's NOCASE).
        """
        sql = "SELECT * FROM books"
        params: tuple[Any, ...] = ()
        if author is not None:
            sql += " WHERE author COLLATE NOCASE = ?"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [_to_book(row) for row in rows]

    def update(self, book_id: int, fields: BookFields) -> Book | None:
        """Replace every writable field of a book. Returns None if it does not exist."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (fields.title, fields.author, fields.year, fields.isbn, book_id),
            )
            if cursor.rowcount == 0:
                return None
        return Book(id=book_id, **asdict(fields))

    def delete(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0

    def ping(self) -> bool:
        """Return True if the database answers a trivial query."""
        try:
            with self._lock:
                self._conn.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _to_book(row: sqlite3.Row) -> Book:
    return Book(id=row["id"], title=row["title"], author=row["author"], year=row["year"], isbn=row["isbn"])
