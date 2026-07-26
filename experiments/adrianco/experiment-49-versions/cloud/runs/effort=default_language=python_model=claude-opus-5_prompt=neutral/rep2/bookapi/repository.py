"""Data access for the books table.

Every function takes an open connection so the caller controls the transaction
boundary (the API opens one connection per request).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

COLUMNS = "id, title, author, year, isbn, created_at, updated_at"


class DuplicateIsbnError(Exception):
    """Raised when an ISBN is already used by another book."""

    def __init__(self, isbn: str) -> None:
        super().__init__(f"A book with ISBN {isbn} already exists")
        self.isbn = isbn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def create(conn: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a book and return the stored row."""
    now = _now()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO books (title, author, year, isbn, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (data["title"], data["author"], data.get("year"), data.get("isbn"), now, now),
            )
    except sqlite3.IntegrityError as exc:
        raise _as_duplicate(exc, data.get("isbn")) from exc
    book = get(conn, int(cursor.lastrowid))
    assert book is not None  # just inserted
    return book


def get(conn: sqlite3.Connection, book_id: int) -> Optional[dict[str, Any]]:
    """Return one book, or None if the id is unknown."""
    row = conn.execute(f"SELECT {COLUMNS} FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_books(conn: sqlite3.Connection, author: Optional[str] = None) -> list[dict[str, Any]]:
    """Return all books, oldest id first, optionally filtered by author.

    The author match is case-insensitive and ignores surrounding whitespace.
    """
    sql = f"SELECT {COLUMNS} FROM books"
    params: tuple[Any, ...] = ()
    if author is not None:
        sql += " WHERE author = ? COLLATE NOCASE"
        params = (author.strip(),)
    sql += " ORDER BY id"
    return [_row_to_dict(row) for row in conn.execute(sql, params)]


def replace(conn: sqlite3.Connection, book_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Overwrite every mutable field of a book. Returns None if the id is unknown."""
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?"
                " WHERE id = ?",
                (
                    data["title"],
                    data["author"],
                    data.get("year"),
                    data.get("isbn"),
                    _now(),
                    book_id,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise _as_duplicate(exc, data.get("isbn")) from exc
    if cursor.rowcount == 0:
        return None
    return get(conn, book_id)


def delete(conn: sqlite3.Connection, book_id: int) -> bool:
    """Delete a book. Returns True if a row was removed."""
    with conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0


def ping(conn: sqlite3.Connection) -> None:
    """Cheap query used by the health check; raises if the database is unusable."""
    conn.execute("SELECT 1 FROM books LIMIT 1").fetchone()


def _as_duplicate(exc: sqlite3.IntegrityError, isbn: Optional[str]) -> Exception:
    if isbn is not None and "books.isbn" in str(exc):
        return DuplicateIsbnError(isbn)
    return exc
