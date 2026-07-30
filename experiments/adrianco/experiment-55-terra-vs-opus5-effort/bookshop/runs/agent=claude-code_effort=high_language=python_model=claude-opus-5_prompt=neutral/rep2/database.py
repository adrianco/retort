"""SQLite persistence for the book collection.

One connection is opened per Flask application context and closed when the
context tears down, so a request never shares a connection with another
thread.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from flask import Flask, current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    author     TEXT NOT NULL,
    year       INTEGER,
    isbn       TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Supports the ?author= filter, which matches case-insensitively.
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""

BOOK_COLUMNS = ("id", "title", "author", "year", "isbn", "created_at", "updated_at")


class DuplicateISBN(Exception):
    """Raised when a write would give two books the same ISBN."""


def init_app(app: Flask) -> None:
    """Wire connection teardown into ``app`` and create the schema."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        get_db().executescript(SCHEMA)
        get_db().commit()


def get_db() -> sqlite3.Connection:
    """Return the connection for the current application context."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        # Enforce the UNIQUE(isbn) constraint and keep writes durable-ish
        # without paying for a full fsync on every statement.
        g.db.execute("PRAGMA journal_mode = WAL")
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ping() -> None:
    """Cheap liveness probe for the health endpoint; raises on failure."""
    get_db().execute("SELECT 1").fetchone()


def list_books(author: str | None = None) -> list[dict[str, Any]]:
    sql = f"SELECT {', '.join(BOOK_COLUMNS)} FROM books"
    params: tuple[Any, ...] = ()
    if author:
        sql += " WHERE author = ? COLLATE NOCASE"
        params = (author,)
    sql += " ORDER BY id"
    return [_as_dict(row) for row in get_db().execute(sql, params)]


def get_book(book_id: int) -> dict[str, Any] | None:
    row = get_db().execute(
        f"SELECT {', '.join(BOOK_COLUMNS)} FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return _as_dict(row) if row is not None else None


def insert_book(data: dict[str, Any]) -> dict[str, Any]:
    now = _utcnow()
    db = get_db()
    with _translate_integrity_errors():
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn"), now, now),
        )
        db.commit()
    created = get_book(int(cursor.lastrowid))
    assert created is not None  # just inserted inside this connection
    return created


def update_book(book_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Apply ``data`` to a book; returns ``None`` if the book does not exist.

    Callers pass a complete field set for PUT and a subset for PATCH; only
    the supplied keys are written.
    """
    fields = [field for field in ("title", "author", "year", "isbn") if field in data]
    if not fields:
        return get_book(book_id)

    assignments = ", ".join(f"{field} = ?" for field in fields)
    params = [data[field] for field in fields]
    params.append(_utcnow())
    params.append(book_id)

    db = get_db()
    with _translate_integrity_errors():
        cursor = db.execute(
            f"UPDATE books SET {assignments}, updated_at = ? WHERE id = ?", params
        )
        db.commit()
    if cursor.rowcount == 0:
        return None
    return get_book(book_id)


def delete_book(book_id: int) -> bool:
    """Delete a book, returning ``True`` if a row was actually removed."""
    db = get_db()
    cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return cursor.rowcount > 0


class _translate_integrity_errors:
    """Turn the UNIQUE(isbn) violation into a domain-level exception."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        if isinstance(exc, sqlite3.IntegrityError) and "books.isbn" in str(exc):
            raise DuplicateISBN("another book already uses this ISBN") from exc
        return False


def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {column: row[column] for column in BOOK_COLUMNS}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
