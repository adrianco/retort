"""SQL for the ``books`` table.

Functions here take an open :class:`sqlite3.Connection` and return plain dicts,
so the HTTP layer never touches SQL and the storage layer never touches Flask.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .errors import ConflictError

COLUMNS = ("id", "title", "author", "year", "isbn", "created_at", "updated_at")
_SELECT = f"SELECT {', '.join(COLUMNS)} FROM books"

#: Fields a client is allowed to write.
WRITABLE = ("title", "author", "year", "isbn")


def _now() -> str:
    """Current UTC time as an ISO-8601 string with a ``Z`` suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_book(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return {key: row[key] for key in COLUMNS} if row is not None else None


def _raise_for_conflict(exc: sqlite3.IntegrityError, isbn: str | None) -> None:
    """Translate the ISBN uniqueness constraint into a 409."""
    if "isbn" in str(exc).lower():
        raise ConflictError(
            f"A book with ISBN {isbn} already exists.",
            details={"isbn": "isbn must be unique across the collection."},
        ) from exc
    raise exc


def create_book(conn: sqlite3.Connection, data: Mapping[str, Any]) -> dict[str, Any]:
    timestamp = _now()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO books (title, author, year, isbn, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data["title"],
                    data["author"],
                    data.get("year"),
                    data.get("isbn"),
                    timestamp,
                    timestamp,
                ),
            )
    except sqlite3.IntegrityError as exc:
        _raise_for_conflict(exc, data.get("isbn"))
        raise  # pragma: no cover - _raise_for_conflict always raises

    book = get_book(conn, cursor.lastrowid)
    assert book is not None  # just inserted
    return book


def get_book(conn: sqlite3.Connection, book_id: int) -> dict[str, Any] | None:
    row = conn.execute(f"{_SELECT} WHERE id = ?", (book_id,)).fetchone()
    return _to_book(row)


def _author_clause(author: str | None) -> tuple[str, list[Any]]:
    if author is None:
        return "", []
    # NOCASE makes ?author= matching case-insensitive, and matches the index.
    return " WHERE author = ? COLLATE NOCASE", [author]


def list_books(
    conn: sqlite3.Connection,
    *,
    author: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    where, params = _author_clause(author)
    sql = f"{_SELECT}{where} ORDER BY id"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    elif offset:
        sql += " LIMIT -1"
    if offset:
        sql += " OFFSET ?"
        params.append(offset)

    rows: Iterable[sqlite3.Row] = conn.execute(sql, params).fetchall()
    return [book for book in (_to_book(row) for row in rows) if book is not None]


def count_books(conn: sqlite3.Connection, *, author: str | None = None) -> int:
    where, params = _author_clause(author)
    return conn.execute(f"SELECT COUNT(*) FROM books{where}", params).fetchone()[0]


def update_book(
    conn: sqlite3.Connection, book_id: int, changes: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Apply ``changes`` to one book; return the new state, or ``None`` if absent.

    A full replacement (PUT) passes every writable field; a patch passes a
    subset. Fields left out of ``changes`` keep their stored value.
    """
    fields = [field for field in WRITABLE if field in changes]
    assignments = [f"{field} = ?" for field in fields] + ["updated_at = ?"]
    params: list[Any] = [changes[field] for field in fields] + [_now(), book_id]

    try:
        with conn:
            cursor = conn.execute(
                f"UPDATE books SET {', '.join(assignments)} WHERE id = ?",
                params,
            )
    except sqlite3.IntegrityError as exc:
        _raise_for_conflict(exc, changes.get("isbn"))
        raise  # pragma: no cover - _raise_for_conflict always raises

    if cursor.rowcount == 0:
        return None
    return get_book(conn, book_id)


def delete_book(conn: sqlite3.Connection, book_id: int) -> bool:
    with conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
