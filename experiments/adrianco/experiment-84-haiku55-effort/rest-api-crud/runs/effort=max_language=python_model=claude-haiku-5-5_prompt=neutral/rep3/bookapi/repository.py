"""SQL access for the books table."""

import sqlite3
from typing import Any

_SELECT = "SELECT id, title, author, year, isbn FROM books"


def insert_book(db: sqlite3.Connection, fields: dict[str, Any]) -> int:
    with db:
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (:title, :author, :year, :isbn)",
            fields,
        )
    return cursor.lastrowid


def list_books(db: sqlite3.Connection, author: str | None = None) -> list[sqlite3.Row]:
    if author is None:
        return db.execute(f"{_SELECT} ORDER BY id").fetchall()
    return db.execute(
        f"{_SELECT} WHERE author = ? COLLATE NOCASE ORDER BY id", (author,)
    ).fetchall()


def get_book(db: sqlite3.Connection, book_id: int) -> sqlite3.Row | None:
    return db.execute(f"{_SELECT} WHERE id = ?", (book_id,)).fetchone()


def update_book(db: sqlite3.Connection, book_id: int, fields: dict[str, Any]) -> bool:
    """Overwrite every field of the book. Returns False if no book has this id."""
    with db:
        cursor = db.execute(
            "UPDATE books SET title = :title, author = :author, year = :year, isbn = :isbn"
            " WHERE id = :id",
            {**fields, "id": book_id},
        )
    return cursor.rowcount == 1


def delete_book(db: sqlite3.Connection, book_id: int) -> bool:
    with db:
        cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount == 1
