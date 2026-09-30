"""SQLite persistence for books."""

import sqlite3
import threading
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

_COLUMNS = ("title", "author", "year", "isbn")


def _casefold(value: Any) -> Any:
    return value.casefold() if isinstance(value, str) else value


def _to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class BookRepository:
    """Thread-safe book store backed by a single SQLite connection.

    One shared connection guarded by a lock keeps ``:memory:`` databases
    working across request threads and is plenty for a small service.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # SQLite's built-in lower()/NOCASE only fold ASCII; this handles Unicode.
        self._conn.create_function("casefold", 1, _casefold, deterministic=True)
        with self._lock, self._conn:
            self._conn.execute(_SCHEMA)

    def create(
        self,
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
            return self._fetch(cursor.lastrowid)  # type: ignore[arg-type]

    def get(self, book_id: int) -> dict[str, Any] | None:
        with self._lock:
            return self._fetch(book_id)

    def list_books(self, author: str | None = None) -> list[dict[str, Any]]:
        """Return books ordered by id, optionally filtered by exact
        (case-insensitive) author name."""
        sql = "SELECT * FROM books"
        params: tuple[Any, ...] = ()
        if author is not None:
            sql += " WHERE casefold(author) = casefold(?)"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            return [_to_dict(row) for row in self._conn.execute(sql, params)]

    def update(self, book_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        """Apply ``fields`` to a book. Returns the updated book, or ``None`` if
        it does not exist."""
        unknown = set(fields) - set(_COLUMNS)
        if unknown:
            raise ValueError(f"unknown book fields: {sorted(unknown)}")
        with self._lock, self._conn:
            if fields:
                assignments = ", ".join(f"{column} = ?" for column in fields)
                self._conn.execute(
                    f"UPDATE books SET {assignments} WHERE id = ?",
                    (*fields.values(), book_id),
                )
            return self._fetch(book_id)

    def delete(self, book_id: int) -> bool:
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

    def _fetch(self, book_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return _to_dict(row) if row else None
