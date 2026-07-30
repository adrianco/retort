"""Data access for the ``books`` table.

Every query here is parameterised; the only value ever interpolated into SQL is
the sort column, and that is looked up in an allow-list first.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from .validation import SORTABLE_FIELDS, WRITABLE_FIELDS

#: Column order used for JSON output.
BOOK_FIELDS = ("id", "title", "author", "year", "isbn", "created_at", "updated_at")

#: Text columns are sorted case-insensitively so "achebe" and "Achebe" group.
_COLLATED = {"title", "author"}


def utcnow() -> str:
    """Current UTC time as an ISO-8601 string, e.g. ``2026-07-29T21:05:00.123Z``."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {field: row[field] for field in BOOK_FIELDS}


def _order_by(sort: str, descending: bool) -> str:
    if sort not in SORTABLE_FIELDS:  # pragma: no cover - guarded by validation
        raise ValueError(f"unsortable column: {sort!r}")
    collate = " COLLATE NOCASE" if sort in _COLLATED else ""
    direction = "DESC" if descending else "ASC"
    # ``id`` breaks ties so pagination is stable across requests.
    return f"ORDER BY {sort}{collate} {direction}, id {direction}"


def _filters(
    author: str | None, title: str | None, year: int | None
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if author is not None:
        # Whole-name match, ignoring case: ?author=chinua%20achebe matches
        # "Chinua Achebe".  Substring search is what ?title= is for.
        clauses.append("author = ? COLLATE NOCASE")
        params.append(author)
    if title is not None:
        # LIKE ignores collating sequences; its own case folding (ASCII-only) is
        # what makes this filter case-insensitive, so no COLLATE clause here.
        clauses.append("title LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(title)}%")
    if year is not None:
        clauses.append("year = ?")
        params.append(year)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def _escape_like(value: str) -> str:
    for char in ("\\", "%", "_"):
        value = value.replace(char, f"\\{char}")
    return value


def list_books(
    connection: sqlite3.Connection,
    *,
    author: str | None = None,
    title: str | None = None,
    year: int | None = None,
    sort: str = "id",
    descending: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Return ``(books, total)`` where ``total`` ignores limit/offset."""
    where, params = _filters(author, title, year)

    total = connection.execute(
        f"SELECT COUNT(*) FROM books {where}", params
    ).fetchone()[0]

    sql = f"SELECT * FROM books {where} {_order_by(sort, descending)}"
    page_params = list(params)
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        page_params += [limit, offset]
    elif offset:
        # SQLite requires a LIMIT before OFFSET; -1 means "no limit".
        sql += " LIMIT -1 OFFSET ?"
        page_params.append(offset)

    rows = connection.execute(sql, page_params).fetchall()
    return [row_to_dict(row) for row in rows], total


def get_book(connection: sqlite3.Connection, book_id: int) -> dict[str, Any] | None:
    row = connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return row_to_dict(row) if row is not None else None


def create_book(
    connection: sqlite3.Connection, fields: Mapping[str, Any]
) -> dict[str, Any]:
    now = utcnow()
    values = (
        fields["title"],
        fields["author"],
        fields.get("year"),
        fields.get("isbn"),
        now,
        now,
    )
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO books (title, author, year, isbn, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            values,
        )
    # Built from what was just written rather than read back, so a concurrent
    # DELETE between the commit and a SELECT cannot turn a successful create
    # into an error.  test_get_book_by_id pins this against what SQLite stores.
    return dict(zip(BOOK_FIELDS, (cursor.lastrowid, *values)))


def update_book(
    connection: sqlite3.Connection, book_id: int, fields: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Apply ``fields`` to a book; returns ``None`` if the book does not exist.

    Callers pass every writable field for a PUT and a subset for a PATCH.
    """
    if not fields:  # pragma: no cover - guarded by validation
        raise ValueError("no fields to update")
    unknown = set(fields) - set(WRITABLE_FIELDS)
    if unknown:  # pragma: no cover - guarded by validation
        raise ValueError(f"not writable: {', '.join(sorted(unknown))}")
    assignments: Iterable[str] = [f"{field} = ?" for field in fields]
    params: list[Any] = list(fields.values())
    params.append(utcnow())
    params.append(book_id)

    with connection:
        cursor = connection.execute(
            f"UPDATE books SET {', '.join(assignments)}, updated_at = ? WHERE id = ?",
            params,
        )
    if cursor.rowcount == 0:
        return None
    return get_book(connection, book_id)


def delete_book(connection: sqlite3.Connection, book_id: int) -> bool:
    with connection:
        cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
