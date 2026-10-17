"""SQLite-backed storage for books."""

from __future__ import annotations

import sqlite3
import threading

from .models import Book, BookFields

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL COLLATE NOCASE,
    year   INTEGER,
    isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author);
"""


class BookRepository:
    """Stores books in SQLite.

    A single connection is shared by all request threads, so every query runs
    under a lock. The lock is reentrant because writes re-read the row they changed.
    """

    def __init__(self, path: str = ":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def create(self, fields: BookFields) -> Book:
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (fields.title, fields.author, fields.year, fields.isbn),
            )
            self._conn.commit()
            return self.get(cursor.lastrowid)

    def get(self, book_id: int) -> Book | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _to_book(row) if row else None

    def list(self, author: str | None = None) -> list[Book]:
        """Return all books in insertion order, optionally only those by ``author``.

        The author match is case-insensitive (ASCII only, as SQLite's NOCASE is).
        """
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                ).fetchall()
        return [_to_book(row) for row in rows]

    def update(self, book_id: int, fields: BookFields) -> Book | None:
        """Replace every stored attribute of the book. Returns None if it does not exist."""
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (fields.title, fields.author, fields.year, fields.isbn, book_id),
            )
            self._conn.commit()
            if cursor.rowcount == 0:
                return None
            return self.get(book_id)

    def delete(self, book_id: int) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cursor.rowcount > 0

    def ping(self) -> None:
        """Raise sqlite3.Error if the database cannot answer a trivial query."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _to_book(row: sqlite3.Row) -> Book:
    return Book(
        id=row["id"],
        title=row["title"],
        author=row["author"],
        year=row["year"],
        isbn=row["isbn"],
    )
