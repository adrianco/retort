"""SQL access for the ``books`` table.

Functions here take a connection and plain dicts, so they are usable (and
testable) without a Flask request in flight.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from .errors import ApiError, ConflictError

BOOK_COLUMNS = "id, title, author, year, isbn, created_at, updated_at"

# SQLite stores 64-bit integers; binding anything wider raises OverflowError,
# which is not a sqlite3.Error and would escape as a 500.
SQLITE_MIN_INTEGER = -(2**63)
SQLITE_MAX_INTEGER = 2**63 - 1


def _storable_id(book_id: int) -> bool:
    """No stored row can have an id SQLite cannot even represent."""
    return SQLITE_MIN_INTEGER <= book_id <= SQLITE_MAX_INTEGER


def utc_now() -> str:
    """Fixed-width UTC timestamp, so string ordering matches time ordering."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def row_to_book(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _isbn_conflict(exc: sqlite3.IntegrityError, isbn: str | None) -> ConflictError:
    """Translate a UNIQUE violation, re-raising anything unexpected."""
    if "isbn" not in str(exc).lower():
        raise exc
    return ConflictError(f"A book with isbn {isbn!r} already exists.")


def list_books(
    conn: sqlite3.Connection, *, author: str | None = None
) -> list[dict[str, Any]]:
    """All books ordered by id, optionally narrowed to one author.

    The author match is exact but case-insensitive (SQLite ``NOCASE``, which
    folds ASCII only).
    """
    sql = f"SELECT {BOOK_COLUMNS} FROM books"
    params: tuple[Any, ...] = ()
    if author:
        sql += " WHERE author = ? COLLATE NOCASE"
        params = (author,)
    sql += " ORDER BY id"
    return [row_to_book(row) for row in conn.execute(sql, params)]


def get_book(conn: sqlite3.Connection, book_id: int) -> dict[str, Any] | None:
    if not _storable_id(book_id):
        return None
    row = conn.execute(
        f"SELECT {BOOK_COLUMNS} FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return row_to_book(row) if row is not None else None


def create_book(conn: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO books (title, author, year, isbn, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (data["title"], data["author"], data["year"], data["isbn"], now, now),
            )
    except sqlite3.IntegrityError as exc:
        raise _isbn_conflict(exc, data["isbn"]) from exc
    book = get_book(conn, cursor.lastrowid)
    if book is None:
        # Only reachable if the row was deleted between the commit and this
        # read. Raise rather than assert, so `python -O` cannot turn it into a
        # 201 with a null body.
        raise ApiError(f"Book {cursor.lastrowid} vanished immediately after insert.")
    return book


def replace_book(
    conn: sqlite3.Connection, book_id: int, data: dict[str, Any]
) -> dict[str, Any] | None:
    """Overwrite every writable column. Returns ``None`` if the id is unknown."""
    if get_book(conn, book_id) is None:
        return None
    try:
        with conn:
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?,"
                " updated_at = ? WHERE id = ?",
                (
                    data["title"],
                    data["author"],
                    data["year"],
                    data["isbn"],
                    utc_now(),
                    book_id,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise _isbn_conflict(exc, data["isbn"]) from exc
    return get_book(conn, book_id)


def delete_book(conn: sqlite3.Connection, book_id: int) -> bool:
    """Returns True if a row was removed, False if the id was already gone."""
    if not _storable_id(book_id):
        return False
    with conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
