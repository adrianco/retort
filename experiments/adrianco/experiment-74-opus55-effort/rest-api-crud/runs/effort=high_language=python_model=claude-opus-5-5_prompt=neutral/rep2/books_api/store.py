"""SQLite persistence for books."""

import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


class DuplicateISBNError(Exception):
    """Raised when a book's ISBN is already used by another book."""


class BookStore:
    """Thread-safe CRUD access to the ``books`` table.

    A single connection is shared behind a lock so that ``:memory:``
    databases work and concurrent requests from the threaded server are
    serialised.
    """

    def __init__(self, path="books.db"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def list(self, author=None):
        sql = "SELECT * FROM books"
        params = ()
        if author is not None:
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author.strip(),)
        sql += " ORDER BY id"
        with self._lock:
            return [dict(row) for row in self._conn.execute(sql, params)]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None

    def create(self, book):
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                        (book["title"], book["author"], book["year"], book["isbn"]),
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBNError(book["isbn"]) from exc
            book_id = cur.lastrowid
        return {"id": book_id, **book}

    def update(self, book_id, book):
        """Replace a book's fields. Returns the updated book, or None if missing."""
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                        (book["title"], book["author"], book["year"], book["isbn"], book_id),
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateISBNError(book["isbn"]) from exc
        if cur.rowcount == 0:
            return None
        return {"id": book_id, **book}

    def delete(self, book_id):
        """Delete a book. Returns True if a row was removed."""
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0
