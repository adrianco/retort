"""SQLite persistence for books."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from .validation import BookFields

# AUTOINCREMENT guarantees that the id of a deleted book is never handed out
# again, so a stale /books/{id} URL can't start pointing at a different book.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    author TEXT    NOT NULL CHECK (length(trim(author)) > 0),
    year   INTEGER,
    isbn   TEXT
);
"""

_COLUMNS = "id, title, author, year, isbn"

Book = dict[str, Any]


def _casefold(value: object) -> object:
    return value.casefold() if isinstance(value, str) else value


class BookRepository:
    """Stores books in a SQLite database.

    A single connection is shared by all request threads and guarded by a
    lock; SQLite serialises writes anyway, and this also makes ``":memory:"``
    databases usable from a multi-threaded server.
    """

    def __init__(self, database: str | Path = ":memory:") -> None:
        database = str(database)
        if database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(database, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # SQLite's own lower()/LIKE only fold ASCII; use Python's full
        # Unicode case folding for the author filter instead.
        self._conn.create_function("casefold", 1, _casefold, deterministic=True)
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def create(self, fields: BookFields) -> Book:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) "
                "VALUES (:title, :author, :year, :isbn)",
                fields,
            )
            book = self._fetch(cursor.lastrowid)
        assert book is not None
        return book

    def get(self, book_id: int) -> Book | None:
        with self._lock:
            return self._fetch(book_id)

    def list_all(self, author: str | None = None) -> list[Book]:
        """Return all books in creation order.

        If ``author`` is given, only books whose author contains it
        (case-insensitively) are returned.
        """
        with self._lock:
            if author is None:
                rows = self._conn.execute(f"SELECT {_COLUMNS} FROM books ORDER BY id")
            else:
                rows = self._conn.execute(
                    f"SELECT {_COLUMNS} FROM books "
                    "WHERE instr(casefold(author), casefold(?)) > 0 ORDER BY id",
                    (author,),
                )
            return [dict(row) for row in rows]

    def update(self, book_id: int, fields: BookFields) -> Book | None:
        """Replace every writable field of a book; ``None`` if it doesn't exist."""
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
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    def ping(self) -> bool:
        """Return True if the database is reachable and the schema is present."""
        try:
            with self._lock:
                self._conn.execute("SELECT 1 FROM books LIMIT 1").fetchall()
        except sqlite3.Error:
            return False
        return True

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _fetch(self, book_id: int | None) -> Book | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row is not None else None
