"""Data-access layer for the ``books`` table.

Every function takes an explicit :class:`sqlite3.Connection` so the storage
layer stays independent of Flask's request context.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

Book = Dict[str, Any]

_COLUMNS = "id, title, author, year, isbn, created_at, updated_at"

#: Columns a client is allowed to write.  Column names cannot be bound as
#: SQL parameters, so :func:`update` interpolates them -- the allow-list keeps
#: that interpolation safe no matter what reaches this layer.
_WRITABLE = frozenset({"title", "author", "year", "isbn"})


def _utcnow() -> str:
    """Current UTC time as ISO-8601, e.g. ``2026-07-25T12:00:00.123Z``.

    Millisecond precision keeps ``updated_at`` meaningful for edits that land
    in the same second as the insert.
    """
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _to_dict(row: Optional[sqlite3.Row]) -> Optional[Book]:
    return dict(row) if row is not None else None


def create(conn: sqlite3.Connection, data: Book) -> Book:
    """Insert a book and return the stored representation."""
    now = _utcnow()
    with conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                data["title"],
                data["author"],
                data.get("year"),
                data.get("isbn"),
                now,
                now,
            ),
        )
    book = get(conn, cursor.lastrowid)
    assert book is not None  # just inserted
    return book


def get(conn: sqlite3.Connection, book_id: int) -> Optional[Book]:
    """Return a single book, or ``None`` when it does not exist."""
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return _to_dict(row)


def list_books(
    conn: sqlite3.Connection,
    author: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Tuple[List[Book], int]:
    """Return ``(books, total_matches)``.

    ``total_matches`` ignores ``limit``/``offset`` so callers can report how
    many rows the filter matched overall.  Matching on ``author`` is exact but
    case-insensitive.
    """
    where, params = "", []
    if author:
        where = " WHERE author = ? COLLATE NOCASE"
        params.append(author)

    total = conn.execute(
        f"SELECT COUNT(*) AS total FROM books{where}", params
    ).fetchone()["total"]

    query = f"SELECT {_COLUMNS} FROM books{where} ORDER BY id ASC"
    if limit is not None or offset:
        # SQLite requires a LIMIT before OFFSET; -1 means "no limit".
        query += " LIMIT ? OFFSET ?"
        params = params + [limit if limit is not None else -1, offset]

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows], total


def update(
    conn: sqlite3.Connection, book_id: int, changes: Book
) -> Optional[Book]:
    """Apply ``changes`` to a book; return ``None`` when it does not exist."""
    unknown = set(changes) - _WRITABLE
    if unknown:
        raise ValueError(f"cannot update unknown column(s): {sorted(unknown)}")
    if not changes:
        raise ValueError("no changes supplied")
    if get(conn, book_id) is None:
        return None

    assignments = [f"{field} = ?" for field in changes]
    params: List[Any] = list(changes.values())
    assignments.append("updated_at = ?")
    params.append(_utcnow())
    params.append(book_id)

    with conn:
        conn.execute(
            f"UPDATE books SET {', '.join(assignments)} WHERE id = ?", params
        )
    return get(conn, book_id)


def delete(conn: sqlite3.Connection, book_id: int) -> bool:
    """Delete a book; return ``True`` when a row was actually removed."""
    with conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
