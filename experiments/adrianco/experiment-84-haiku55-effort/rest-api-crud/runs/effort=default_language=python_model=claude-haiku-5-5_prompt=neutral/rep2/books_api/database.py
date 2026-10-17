"""SQLite-backed storage for books."""

import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
)
"""

_COLUMNS = ("id", "title", "author", "year", "isbn")


class ConflictError(Exception):
    """A write violated a uniqueness constraint (e.g. a duplicate ISBN)."""


class BookRepository:
    """Stores books in a single SQLite database.

    The HTTP server handles requests on several threads, so the one connection
    is shared and every access is serialised by a re-entrant lock.
    """

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock, self._conn:
            self._conn.execute(_SCHEMA)

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, data):
        with self._lock:
            cursor = self._execute_write(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data["year"], data["isbn"]),
            )
            return self.get(cursor.lastrowid)

    def find(self, author=None):
        """Return all books in insertion order, optionally filtered by author.

        The author filter is an exact match that ignores ASCII case.
        """
        sql = "SELECT * FROM books"
        params = []
        if author is not None:
            sql += " WHERE LOWER(author) = LOWER(?)"
            params.append(author)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_dict(row) if row else None

    def update(self, book_id, data):
        """Replace every field of a book. Returns the updated book, or None if it does not exist."""
        with self._lock:
            cursor = self._execute_write(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data["title"], data["author"], data["year"], data["isbn"], book_id),
            )
            if cursor.rowcount == 0:
                return None
            return self.get(book_id)

    def delete(self, book_id):
        """Delete a book. Returns True if a book was removed."""
        with self._lock:
            cursor = self._execute_write("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    def _execute_write(self, sql, params):
        try:
            with self._conn:  # commits on success, rolls back on error
                return self._conn.execute(sql, params)
        except sqlite3.IntegrityError as exc:
            raise ConflictError(str(exc)) from exc


def _row_to_dict(row):
    return {column: row[column] for column in _COLUMNS}
