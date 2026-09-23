"""SQLite persistence for books.

Each request lazily opens its own connection, kept on ``flask.g`` and closed
when the application context ends.
"""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g

Book = dict[str, Any]

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    -- AUTOINCREMENT: the id of a deleted book is never handed out again
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

_SELECT_BOOKS = "SELECT id, title, author, year, isbn FROM books"

#: SQLite integers are signed 64-bit, so no book can have a larger id; binding
#: one to a query would raise OverflowError instead of finding nothing.
MAX_ID = 2**63 - 1


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a connection whose rows convert to dicts."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    # Unicode-aware case folding for the author filter; SQLite's own LIKE and
    # NOCASE only fold ASCII letters.
    connection.create_function("casefold", 1, str.casefold, deterministic=True)
    return connection


def init_app(app: Flask) -> None:
    """Create the database file and schema if missing, and register cleanup."""
    path = Path(app.config["DATABASE"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as connection:
        connection.execute(SCHEMA)
        connection.commit()
    app.teardown_appcontext(_close_db)


def get_db() -> sqlite3.Connection:
    """The current request's connection, opened on first use."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def _close_db(_error: BaseException | None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def ping() -> None:
    """Raise sqlite3.Error unless the books table can be queried."""
    get_db().execute("SELECT 1 FROM books LIMIT 1").fetchall()


def list_books(author: str | None = None) -> list[Book]:
    """Books in id order; with *author*, those whose author contains it (any case)."""
    query = _SELECT_BOOKS
    params: tuple[str, ...] = ()
    if author:
        query += " WHERE instr(casefold(author), casefold(?)) > 0"
        params = (author,)
    rows = get_db().execute(query + " ORDER BY id", params).fetchall()
    return [dict(row) for row in rows]


def get_book(book_id: int) -> Book | None:
    """The book with *book_id*, or None if there is no such book."""
    if book_id > MAX_ID:
        return None
    query = _SELECT_BOOKS + " WHERE id = ?"
    row = get_db().execute(query, (book_id,)).fetchone()
    return dict(row) if row is not None else None


def create_book(fields: Book) -> Book:
    """Insert a validated book and return it with its new id."""
    connection = get_db()
    with connection:
        cursor = connection.execute(
            "INSERT INTO books (title, author, year, isbn)"
            " VALUES (:title, :author, :year, :isbn)",
            fields,
        )
    return {"id": cursor.lastrowid, **fields}


def update_book(book_id: int, fields: Book) -> Book | None:
    """Replace every field of a book; None if there is no such book."""
    if book_id > MAX_ID:
        return None
    connection = get_db()
    with connection:
        cursor = connection.execute(
            "UPDATE books SET title = :title, author = :author, year = :year,"
            " isbn = :isbn WHERE id = :id",
            {**fields, "id": book_id},
        )
    return {"id": book_id, **fields} if cursor.rowcount else None


def delete_book(book_id: int) -> bool:
    """Delete a book; False if there was no such book."""
    if book_id > MAX_ID:
        return False
    connection = get_db()
    with connection:
        cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
