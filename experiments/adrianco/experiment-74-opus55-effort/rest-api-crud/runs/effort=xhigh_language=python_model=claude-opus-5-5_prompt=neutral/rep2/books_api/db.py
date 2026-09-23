"""SQLite persistence for books."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

# AUTOINCREMENT guarantees that the id of a deleted book is never handed out
# again, so a stale /books/{id} URL keeps returning 404 instead of another book.
SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

EDITABLE_COLUMNS = ("title", "author", "year", "isbn")
_SELECT = "SELECT id, title, author, year, isbn FROM books"

Book = dict[str, Any]


def _casefold(value: Any) -> Any:
    # SQLite's built-in lower() only folds ASCII; this handles "Ö", "ß", etc.
    return value.casefold() if isinstance(value, str) else value


class BookRepository:
    """CRUD access to the ``books`` table.

    One connection is shared by every thread and serialised with a lock. That
    keeps the repository safe behind the threaded HTTP server, and it also makes
    ``":memory:"`` usable, because every new connection to ``":memory:"`` would
    otherwise open its own empty database.
    """

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.create_function("casefold", 1, _casefold, deterministic=True)
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(SCHEMA)

    def __enter__(self) -> BookRepository:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def ping(self) -> None:
        """Run a trivial query. Raises ``sqlite3.Error`` if the database is unusable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create_book(self, data: dict[str, Any]) -> Book:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn")),
            )
            book = self._fetch(cursor.lastrowid)
        assert book is not None
        return book

    def list_books(self, author: str | None = None) -> list[Book]:
        """Return all books ordered by id.

        ``author`` keeps only books whose author contains that text, ignoring case.
        """
        sql, params = _SELECT, ()
        if author:
            sql += " WHERE instr(casefold(author), ?) > 0"
            params = (author.casefold(),)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_book(self, book_id: int) -> Book | None:
        with self._lock:
            return self._fetch(book_id)

    def update_book(self, book_id: int, changes: dict[str, Any]) -> Book | None:
        """Apply ``changes`` to a book and return the result, or None if the book doesn't exist."""
        unknown = set(changes) - set(EDITABLE_COLUMNS)
        if unknown:
            raise ValueError(f"cannot update unknown columns: {sorted(unknown)}")
        with self._lock, self._conn:
            if changes:
                # Column names are interpolated only after the whitelist check above.
                assignments = ", ".join(f"{column} = ?" for column in changes)
                cursor = self._conn.execute(
                    f"UPDATE books SET {assignments} WHERE id = ?",
                    (*changes.values(), book_id),
                )
                if cursor.rowcount == 0:
                    return None
            return self._fetch(book_id)

    def delete_book(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0

    def _fetch(self, book_id: int | None) -> Book | None:
        row = self._conn.execute(f"{_SELECT} WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row is not None else None
