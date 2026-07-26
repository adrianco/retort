"""SQLite persistence for the book collection.

A single connection is shared behind a lock. SQLite serialises writes anyway,
and a lock keeps the semantics identical for file-backed and ``:memory:``
databases (an in-memory database cannot be reopened from another connection).
"""

from __future__ import annotations

import sqlite3
import threading
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    author     TEXT NOT NULL,
    year       INTEGER,
    isbn       TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
"""

_NOW = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"

BOOK_FIELDS = ("id", "title", "author", "year", "isbn", "created_at", "updated_at")


class BookNotFound(LookupError):
    """Raised when an operation targets a book id that does not exist."""

    def __init__(self, book_id: Any):
        super().__init__(f"Book {book_id!r} not found")
        self.book_id = book_id


class Database:
    """Thin data-access layer over the ``books`` table."""

    def __init__(self, path: str = ":memory:"):
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            if path != ":memory:":
                self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- health ---------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the database answers a trivial query."""
        try:
            with self._lock:
                self._conn.execute("SELECT 1 FROM books LIMIT 1").fetchall()
            return True
        except sqlite3.Error:
            return False

    # -- CRUD -----------------------------------------------------------

    def create(self, book: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn, created_at, updated_at) "
                f"VALUES (?, ?, ?, ?, {_NOW}, {_NOW})",
                (book["title"], book["author"], book.get("year"), book.get("isbn")),
            )
            self._conn.commit()
            return self._require(cursor.lastrowid)

    def list(self, author: str | None = None) -> list[dict[str, Any]]:
        """Return all books, newest first.

        ``author`` filters case-insensitively on any substring of the author
        name, so ``?author=orwell`` matches "George Orwell".
        """
        sql = f"SELECT {', '.join(BOOK_FIELDS)} FROM books"
        params: tuple[Any, ...] = ()
        if author is not None and author.strip():
            # ESCAPE guards against a user-supplied % or _ acting as a wildcard.
            sql += " WHERE author LIKE ? ESCAPE '\\'"
            params = (f"%{_escape_like(author.strip())}%",)
        sql += " ORDER BY id DESC"

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                f"SELECT {', '.join(BOOK_FIELDS)} FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def update(self, book_id: int, book: dict[str, Any]) -> dict[str, Any]:
        """Replace a book's fields. Raises BookNotFound if the id is unknown."""
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, "
                f"updated_at = {_NOW} WHERE id = ?",
                (
                    book["title"],
                    book["author"],
                    book.get("year"),
                    book.get("isbn"),
                    book_id,
                ),
            )
            if cursor.rowcount == 0:
                raise BookNotFound(book_id)
            self._conn.commit()
            return self._require(book_id)

    def delete(self, book_id: int) -> None:
        """Delete a book. Raises BookNotFound if the id is unknown."""
        with self._lock:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if cursor.rowcount == 0:
                raise BookNotFound(book_id)
            self._conn.commit()

    # -- internal -------------------------------------------------------

    def _require(self, book_id: int) -> dict[str, Any]:
        book = self.get(book_id)
        if book is None:  # pragma: no cover - only reachable on concurrent DELETE
            raise BookNotFound(book_id)
        return book


def _escape_like(value: str) -> str:
    for char in ("\\", "%", "_"):
        value = value.replace(char, "\\" + char)
    return value
