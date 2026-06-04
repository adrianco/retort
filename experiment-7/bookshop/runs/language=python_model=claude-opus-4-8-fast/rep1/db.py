"""SQLite persistence layer for the book collection service."""

import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

DEFAULT_DB_PATH = "books.db"


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create the books table if it does not yet exist."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                author TEXT NOT NULL,
                year   INTEGER,
                isbn   TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn(db_path: str = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a connection that is committed/closed on exit."""
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_book(
    conn: sqlite3.Connection,
    title: str,
    author: str,
    year: Optional[int],
    isbn: Optional[str],
) -> dict:
    cur = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn),
    )
    return get_book(conn, cur.lastrowid)


def list_books(conn: sqlite3.Connection, author: Optional[str] = None) -> list:
    if author is not None:
        rows = conn.execute(
            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_book(conn: sqlite3.Connection, book_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_dict(row) if row else None


def update_book(
    conn: sqlite3.Connection,
    book_id: int,
    title: str,
    author: str,
    year: Optional[int],
    isbn: Optional[str],
) -> Optional[dict]:
    cur = conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id),
    )
    if cur.rowcount == 0:
        return None
    return get_book(conn, book_id)


def delete_book(conn: sqlite3.Connection, book_id: int) -> bool:
    cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cur.rowcount > 0
