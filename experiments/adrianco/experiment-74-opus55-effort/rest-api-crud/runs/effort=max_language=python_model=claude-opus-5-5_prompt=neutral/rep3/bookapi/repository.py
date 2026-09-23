"""Data access for books, free of any HTTP concerns."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

Book = dict[str, Any]


class BookRepository:
    """CRUD operations on the ``books`` table over one connection.

    Write methods take the clean fields produced by
    :func:`bookapi.validation.validate_book`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def find(self, author: str | None = None) -> list[Book]:
        """All books in ID order; with *author*, only those whose author
        contains it, ignoring case."""
        if author is None:
            rows = self._conn.execute(
                "SELECT id, title, author, year, isbn FROM books ORDER BY id"
            )
        else:
            rows = self._conn.execute(
                "SELECT id, title, author, year, isbn FROM books"
                " WHERE instr(casefold(author), ?) > 0 ORDER BY id",
                (author.casefold(),),
            )
        return [dict(row) for row in rows]

    def get(self, book_id: int) -> Book | None:
        row = self._conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def create(self, fields: Mapping[str, Any]) -> Book:
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn)"
                " VALUES (:title, :author, :year, :isbn)",
                fields,
            )
        return {"id": cursor.lastrowid, **fields}

    def replace(self, book_id: int, fields: Mapping[str, Any]) -> Book | None:
        """Overwrite every field of the book; ``None`` if it does not exist."""
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = :title, author = :author, year = :year,"
                " isbn = :isbn WHERE id = :id",
                {**fields, "id": book_id},
            )
        return {"id": book_id, **fields} if cursor.rowcount else None

    def delete(self, book_id: int) -> bool:
        """Delete the book, returning whether it existed."""
        with self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0
