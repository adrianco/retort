"""SQLite persistence for the Book Collection API.

Plain ``sqlite3`` from the standard library -- no ORM. A fresh connection is
opened per request (see :func:`get_connection`) which keeps things safe when
FastAPI runs sync endpoints on its worker thread pool.

The database file is chosen by the ``BOOKS_DB_PATH`` environment variable and
defaults to ``books.db`` in the working directory. Tests point it at a
temporary file.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional

DEFAULT_DB_PATH = "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT    UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
"""

_COLUMNS = ("id", "title", "author", "year", "isbn")
_WRITABLE = ("title", "author", "year", "isbn")
_SELECT = f"SELECT {', '.join(_COLUMNS)} FROM books"


def get_db_path() -> str:
    """Path to the SQLite file, resolved fresh on every call so tests can swap it."""
    return os.environ.get("BOOKS_DB_PATH") or DEFAULT_DB_PATH


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Optional[str] = None) -> None:
    """Create the schema if it does not exist yet. Safe to call repeatedly."""
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_connection(path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    return dict(row) if row is not None else None


def _escape_like(term: str) -> str:
    """Neutralise LIKE wildcards in user input (used with ``ESCAPE '\\'``)."""
    for char in ("\\", "%", "_"):
        term = term.replace(char, "\\" + char)
    return term


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #

def create_book(conn: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a book and return it. Raises ``sqlite3.IntegrityError`` on a duplicate ISBN."""
    cursor = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (data["title"], data["author"], data.get("year"), data.get("isbn")),
    )
    conn.commit()
    book = get_book(conn, int(cursor.lastrowid))
    assert book is not None  # just inserted
    return book


def list_books(
    conn: sqlite3.Connection,
    author: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """All books ordered by id, optionally filtered by (partial, case-insensitive) author."""
    sql = _SELECT
    params: list[Any] = []
    if author is not None:
        sql += " WHERE lower(author) LIKE ? ESCAPE '\\'"
        params.append(f"%{_escape_like(author.lower())}%")
    sql += " ORDER BY id"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    elif offset:
        sql += " LIMIT -1 OFFSET ?"
        params.append(offset)
    return [dict(row) for row in conn.execute(sql, params)]


def get_book(conn: sqlite3.Connection, book_id: int) -> Optional[dict[str, Any]]:
    row = conn.execute(f"{_SELECT} WHERE id = ?", (book_id,)).fetchone()
    return _row_to_dict(row)


def replace_book(
    conn: sqlite3.Connection, book_id: int, data: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """Full update (PUT). Returns ``None`` if the book does not exist."""
    cursor = conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (data["title"], data["author"], data.get("year"), data.get("isbn"), book_id),
    )
    if cursor.rowcount == 0:
        return None
    conn.commit()
    return get_book(conn, book_id)


def update_book(
    conn: sqlite3.Connection, book_id: int, changes: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """Partial update (PATCH). Returns ``None`` if the book does not exist."""
    fields = [name for name in _WRITABLE if name in changes]
    if not fields:
        return get_book(conn, book_id)
    assignments = ", ".join(f"{name} = ?" for name in fields)
    params = [changes[name] for name in fields] + [book_id]
    cursor = conn.execute(f"UPDATE books SET {assignments} WHERE id = ?", params)
    if cursor.rowcount == 0:
        return None
    conn.commit()
    return get_book(conn, book_id)


def delete_book(conn: sqlite3.Connection, book_id: int) -> bool:
    """Delete a book, returning ``True`` if a row was actually removed."""
    cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    return cursor.rowcount > 0


def ping(conn: sqlite3.Connection) -> None:
    """Cheap liveness probe for the health check."""
    conn.execute("SELECT 1 FROM books LIMIT 1").fetchone()
