"""Data access for book records.

Every function takes an explicit :class:`sqlite3.Connection` so the storage
layer stays independent of the web framework.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

FIELDS = ("id", "title", "author", "year", "isbn", "created_at", "updated_at")


class DuplicateISBNError(Exception):
    """Raised when a write would store an ISBN that already exists."""

    def __init__(self, isbn: str) -> None:
        super().__init__(f"A book with ISBN {isbn} already exists")
        self.isbn = isbn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {field: row[field] for field in FIELDS}


def create(connection: sqlite3.Connection, book: dict[str, Any]) -> dict[str, Any]:
    """Insert a book and return it, including its generated id."""
    timestamp = _now()
    try:
        cursor = connection.execute(
            """
            INSERT INTO books (title, author, year, isbn, created_at, updated_at)
            VALUES (:title, :author, :year, :isbn, :created_at, :updated_at)
            """,
            {**book, "created_at": timestamp, "updated_at": timestamp},
        )
    except sqlite3.IntegrityError as exc:
        _reraise_duplicate_isbn(book, exc)
    return get(connection, cursor.lastrowid)


def list_all(
    connection: sqlite3.Connection, *, author: str | None = None
) -> list[dict[str, Any]]:
    """Return all books, newest first, optionally filtered by exact author.

    The author comparison is case-insensitive; surrounding whitespace in the
    filter is ignored.
    """
    sql = "SELECT * FROM books"
    params: list[Any] = []
    if author is not None:
        sql += " WHERE author = ? COLLATE NOCASE"
        params.append(author.strip())
    sql += " ORDER BY id DESC"
    return [_to_dict(row) for row in connection.execute(sql, params)]


def get(connection: sqlite3.Connection, book_id: int) -> dict[str, Any] | None:
    """Return a single book, or ``None`` if no book has that id."""
    row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _to_dict(row) if row is not None else None


def replace(
    connection: sqlite3.Connection, book_id: int, book: dict[str, Any]
) -> dict[str, Any] | None:
    """Overwrite a book's fields. Returns ``None`` if the book does not exist."""
    try:
        cursor = connection.execute(
            """
            UPDATE books
               SET title = :title,
                   author = :author,
                   year = :year,
                   isbn = :isbn,
                   updated_at = :updated_at
             WHERE id = :id
            """,
            {**book, "id": book_id, "updated_at": _now()},
        )
    except sqlite3.IntegrityError as exc:
        _reraise_duplicate_isbn(book, exc)
    if cursor.rowcount == 0:
        return None
    return get(connection, book_id)


def delete(connection: sqlite3.Connection, book_id: int) -> bool:
    """Delete a book, returning whether a row was actually removed."""
    cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0


def _reraise_duplicate_isbn(
    book: dict[str, Any], exc: sqlite3.IntegrityError
) -> None:
    """Translate a UNIQUE(isbn) violation; let anything else propagate as-is."""
    if "books.isbn" in str(exc):
        raise DuplicateISBNError(book["isbn"]) from exc
    raise exc
