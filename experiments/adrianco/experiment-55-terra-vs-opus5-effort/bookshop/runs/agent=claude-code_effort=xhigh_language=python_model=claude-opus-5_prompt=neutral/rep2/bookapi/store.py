"""Data access for the ``books`` table.

Every function takes an open connection and returns plain dicts, keeping SQL out
of the HTTP layer.
"""

from __future__ import annotations

import sqlite3

_COLUMNS = "id, title, author, year, isbn"


def list_books(conn: sqlite3.Connection, author: str | None = None) -> list[dict]:
    """Return all books, optionally filtered by exact (case-insensitive) author."""
    sql = f"SELECT {_COLUMNS} FROM books"
    params: list[object] = []
    if author and author.strip():
        sql += " WHERE author = ? COLLATE NOCASE"
        params.append(author.strip())
    sql += " ORDER BY id"
    return [dict(row) for row in conn.execute(sql, params)]


def get_book(conn: sqlite3.Connection, book_id: int) -> dict | None:
    """Return a single book, or ``None`` if no such id exists."""
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return dict(row) if row else None


def create_book(conn: sqlite3.Connection, fields: dict) -> dict:
    """Insert a book and return the stored representation."""
    cur = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (fields["title"], fields["author"], fields.get("year"), fields.get("isbn")),
    )
    conn.commit()
    book = get_book(conn, cur.lastrowid)
    assert book is not None  # just inserted
    return book


def update_book(conn: sqlite3.Connection, book_id: int, fields: dict) -> dict | None:
    """Apply ``fields`` to a book and return it, or ``None`` if it is missing.

    ``fields`` may hold any subset of the writable columns, which makes this
    usable for both a full PUT replacement and a partial PATCH.
    """
    if get_book(conn, book_id) is None:
        return None
    if fields:
        # Column names come from validate_book()'s whitelist, never from raw
        # client input, so interpolating them into the statement is safe.
        assignments = ", ".join(f"{name} = ?" for name in fields)
        conn.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*fields.values(), book_id),
        )
        conn.commit()
    return get_book(conn, book_id)


def delete_book(conn: sqlite3.Connection, book_id: int) -> bool:
    """Delete a book, returning whether it existed."""
    cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    return cur.rowcount > 0
