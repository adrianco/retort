"""Data access for the ``books`` table."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from .db import get_db
from .errors import ApiError

_COLUMNS = "id, title, author, year, isbn, created_at, updated_at"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _serialise(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _duplicate_isbn_error(isbn: str | None) -> ApiError:
    return ApiError(
        409,
        "duplicate_isbn",
        "A book with that ISBN already exists.",
        details={"isbn": isbn},
    )


def list_books(author: str | None = None) -> list[dict[str, Any]]:
    """Return all books, optionally narrowed to a case-insensitive author match."""
    sql = f"SELECT {_COLUMNS} FROM books"
    params: list[Any] = []
    if author:
        # Escape LIKE wildcards so a search for "100%" is a literal search.
        pattern = author.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " WHERE author LIKE ? ESCAPE '\\'"
        params.append(f"%{pattern}%")
    sql += " ORDER BY id"
    return [_serialise(row) for row in get_db().execute(sql, params)]


def get_book(book_id: int) -> dict[str, Any] | None:
    row = get_db().execute(
        f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return _serialise(row) if row else None


def create_book(book: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (book["title"], book["author"], book["year"], book["isbn"], now, now),
        )
    except sqlite3.IntegrityError as exc:
        raise _duplicate_isbn_error(book["isbn"]) from exc
    db.commit()
    return get_book(cursor.lastrowid)  # type: ignore[return-value]


def replace_book(book_id: int, book: dict[str, Any]) -> dict[str, Any] | None:
    """Overwrite a book in place. Returns ``None`` if the book does not exist."""
    db = get_db()
    try:
        cursor = db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?"
            " WHERE id = ?",
            (book["title"], book["author"], book["year"], book["isbn"], _now(), book_id),
        )
    except sqlite3.IntegrityError as exc:
        raise _duplicate_isbn_error(book["isbn"]) from exc
    db.commit()
    if cursor.rowcount == 0:
        return None
    return get_book(book_id)


def delete_book(book_id: int) -> bool:
    """Delete a book, returning whether a row was actually removed."""
    db = get_db()
    cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return cursor.rowcount > 0


def ping() -> None:
    """Raise if the database is not reachable."""
    get_db().execute("SELECT 1").fetchone()
