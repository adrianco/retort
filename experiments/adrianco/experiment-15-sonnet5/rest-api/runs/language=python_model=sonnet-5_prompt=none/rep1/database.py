"""SQLite data access layer for the book collection service."""

import sqlite3
from typing import Any, Optional

DEFAULT_DB_PATH = "books.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
            """
        )


def create_book(
    db_path: str, title: str, author: str, year: Optional[int], isbn: Optional[str]
) -> dict[str, Any]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        book_id = cursor.lastrowid
    return get_book(db_path, book_id)


def list_books(db_path: str, author: Optional[str] = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author LIKE ? ORDER BY id",
                (f"%{author}%",),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_book(db_path: str, book_id: int) -> Optional[dict[str, Any]]:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return dict(row) if row else None


def update_book(
    db_path: str, book_id: int, title: str, author: str, year: Optional[int], isbn: Optional[str]
) -> Optional[dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        if cursor.rowcount == 0:
            return None
    return get_book(db_path, book_id)


def delete_book(db_path: str, book_id: int) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
