"""SQLite persistence for books."""

import sqlite3
import threading
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,  -- AUTOINCREMENT: ids are never reused
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


def _casefold(value: str | None) -> str | None:
    # SQLite's LOWER() and NOCASE only fold ASCII. Python's casefold also
    # handles accented names such as "Émile Zola".
    return None if value is None else value.casefold()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class BookStore:
    """Books kept in one SQLite database.

    The HTTP server handles each request on its own thread, and a sqlite3
    connection must not be used from several threads at once, so every
    operation holds a lock.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.create_function("casefold", 1, _casefold, deterministic=True)
        self._conn.executescript(SCHEMA)

    def create(
        self,
        *,
        title: str,
        author: str,
        year: int | None = None,
        isbn: str | None = None,
    ) -> dict[str, Any]:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
        return {"id": cursor.lastrowid, "title": title, "author": author, "year": year, "isbn": isbn}

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return None if row is None else _row_to_dict(row)

    def list_books(self, author: str | None = None) -> list[dict[str, Any]]:
        """Return all books in id order, optionally only those by ``author``.

        The author match is case-insensitive and must otherwise be exact.
        """
        sql = "SELECT * FROM books"
        params: tuple[str, ...] = ()
        if author is not None:
            sql += " WHERE casefold(author) = casefold(?)"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]

    def update(self, book_id: int, changes: dict[str, Any]) -> dict[str, Any] | None:
        """Apply ``changes`` to a book. Returns the updated book, or None if it does not exist."""
        with self._lock, self._conn:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                return None
            book = {**_row_to_dict(row), **changes}
            self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
        return book

    def delete(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0

    def ping(self) -> None:
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
