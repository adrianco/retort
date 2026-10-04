"""SQLite persistence for books."""

import sqlite3
import threading

# AUTOINCREMENT guarantees an id is never reused after its book is deleted,
# so a stale URL can never silently start pointing at a different book.
SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author);
"""

COLUMNS = "id, title, author, year, isbn"


class BookStore:
    """CRUD access to the ``books`` table.

    One connection is shared by all threads and guarded by a lock. That keeps
    ``:memory:`` databases usable (each new connection to ``:memory:`` would
    otherwise see its own empty database) and is plenty for this workload.
    """

    def __init__(self, path=":memory:"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        """Raise ``sqlite3.Error`` if the database cannot be queried."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, book):
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
        return {"id": cursor.lastrowid, **book}

    def list(self, author=None):
        query = f"SELECT {COLUMNS} FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ?"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute(
                f"SELECT {COLUMNS} FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return dict(row) if row else None

    def update(self, book_id, book):
        """Replace the book's fields. Returns ``None`` if it does not exist."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
        if cursor.rowcount == 0:
            return None
        return {"id": book_id, **book}

    def delete(self, book_id):
        """Returns ``True`` if a book was deleted, ``False`` if none existed."""
        with self._lock, self._conn:
            cursor = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0
