"""Data access for the book resource.

Every function takes an open :class:`sqlite3.Connection` and returns plain
dicts, keeping SQL out of the HTTP layer and making the queries directly
testable without a request context.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from .errors import ConflictError

#: Table columns a client can write, and the order used in responses.
COLUMNS: tuple[str, ...] = ("title", "author", "year", "isbn")

_SELECT = "SELECT id, title, author, year, isbn FROM books"


def _to_book(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _conflict(isbn: str | None) -> ConflictError:
    return ConflictError(
        f"A book with ISBN {isbn!r} already exists.",
        details={"isbn": "'isbn' must be unique."},
    )


def list_books(
    connection: sqlite3.Connection, author: str | None = None
) -> list[dict[str, Any]]:
    """Return all books, optionally filtered by exact (case-insensitive) author."""
    sql, params = _SELECT, []
    if author is not None:
        # The explicit COLLATE applies NOCASE to the comparison itself.
        sql += " WHERE author = ? COLLATE NOCASE"
        params.append(author)
    sql += " ORDER BY id"
    return [_to_book(row) for row in connection.execute(sql, params)]


def get_book(connection: sqlite3.Connection, book_id: int) -> dict[str, Any] | None:
    """Return one book, or ``None`` if no book has that id."""
    row = connection.execute(f"{_SELECT} WHERE id = ?", (book_id,)).fetchone()
    return _to_book(row) if row is not None else None


def create_book(
    connection: sqlite3.Connection, data: dict[str, Any]
) -> dict[str, Any]:
    """Insert a book and return it, including its generated id."""
    params = (data["title"], data["author"], data.get("year"), data.get("isbn"))
    try:
        with connection:  # commits on success, rolls back on error
            cursor = connection.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                params,
            )
    except sqlite3.IntegrityError as error:
        raise _conflict(data.get("isbn")) from error

    created = get_book(connection, cursor.lastrowid)
    assert created is not None  # just inserted inside a committed transaction
    return created


def replace_book(
    connection: sqlite3.Connection, book_id: int, data: dict[str, Any]
) -> dict[str, Any] | None:
    """Overwrite every field of a book (PUT). Omitted optional fields become NULL.

    Returns the updated book, or ``None`` if no book has that id.
    """
    params = (
        data["title"],
        data["author"],
        data.get("year"),
        data.get("isbn"),
        book_id,
    )
    try:
        with connection:
            cursor = connection.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? "
                "WHERE id = ?",
                params,
            )
    except sqlite3.IntegrityError as error:
        raise _conflict(data.get("isbn")) from error

    if cursor.rowcount == 0:
        return None
    return get_book(connection, book_id)


def update_book(
    connection: sqlite3.Connection, book_id: int, changes: dict[str, Any]
) -> dict[str, Any] | None:
    """Update only the supplied fields of a book (PATCH).

    Returns the updated book, or ``None`` if no book has that id.
    """
    # Column names are taken from COLUMNS rather than from the caller's keys, so
    # nothing client-controlled is ever interpolated into the statement.
    fields = [column for column in COLUMNS if column in changes]
    if not fields:
        return get_book(connection, book_id)

    assignments = ", ".join(f"{field} = ?" for field in fields)
    params = [changes[field] for field in fields] + [book_id]
    try:
        with connection:
            cursor = connection.execute(
                f"UPDATE books SET {assignments} WHERE id = ?", params
            )
    except sqlite3.IntegrityError as error:
        raise _conflict(changes.get("isbn")) from error

    if cursor.rowcount == 0:
        return None
    return get_book(connection, book_id)


def delete_book(connection: sqlite3.Connection, book_id: int) -> bool:
    """Delete a book. Returns ``True`` if a row was removed."""
    with connection:
        cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
