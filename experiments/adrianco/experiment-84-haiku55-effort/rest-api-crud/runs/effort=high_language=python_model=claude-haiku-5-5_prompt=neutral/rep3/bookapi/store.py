"""SQLite persistence for books."""

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

COLUMNS = ("title", "author", "year", "isbn")


def _values(data):
    return tuple(data[column] for column in COLUMNS)


class BookStore:
    """Stores books in a SQLite database.

    A single connection is shared across threads and guarded by a lock, so the
    store is safe to use from a threaded WSGI server.
    """

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute(SCHEMA)

    def close(self):
        self._conn.close()

    def ping(self):
        """Raise sqlite3.Error if the database is not usable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create_book(self, data):
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                _values(data),
            )
            return self._fetch(cursor.lastrowid)

    def get_book(self, book_id):
        with self._lock:
            return self._fetch(book_id)

    def list_books(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author COLLATE NOCASE = ?"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_book(self, book_id, data):
        """Replace the book's fields. Returns the updated book, or None if missing."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (*_values(data), book_id),
            )
            if cursor.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete_book(self, book_id):
        """Delete the book. Returns False if no such book exists."""
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    def _fetch(self, book_id):
        # Caller must hold self._lock.
        row = self._conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row is not None else None
