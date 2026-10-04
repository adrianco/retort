"""SQLite persistence for the book collection."""

import sqlite3
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
)
"""

FIELDS = ("title", "author", "year", "isbn")


class DuplicateISBN(Exception):
    """Raised when a book's ISBN is already used by another book."""


class BookStore:
    """Book storage backed by a SQLite file.

    A connection is opened per operation, so one store can be shared between
    the threads of a threaded server.
    """

    def __init__(self, path):
        self.path = str(path)
        with closing(self._connect()) as conn, conn:
            conn.execute(SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, book):
        with closing(self._connect()) as conn, conn:
            try:
                cur = conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    [book[f] for f in FIELDS],
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBN(book["isbn"]) from exc
            return {"id": cur.lastrowid, **book}

    def list(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = []
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params.append(author)
        query += " ORDER BY id"
        with closing(self._connect()) as conn:
            return [dict(row) for row in conn.execute(query, params)]

    def get(self, book_id):
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        return dict(row) if row else None

    def update(self, book_id, book):
        """Replace a book. Returns the updated book, or None if it doesn't exist."""
        with closing(self._connect()) as conn, conn:
            try:
                cur = conn.execute(
                    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                    [book[f] for f in FIELDS] + [book_id],
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBN(book["isbn"]) from exc
            if cur.rowcount == 0:
                return None
            return {"id": book_id, **book}

    def delete(self, book_id):
        """Delete a book. Returns False if it doesn't exist."""
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0
