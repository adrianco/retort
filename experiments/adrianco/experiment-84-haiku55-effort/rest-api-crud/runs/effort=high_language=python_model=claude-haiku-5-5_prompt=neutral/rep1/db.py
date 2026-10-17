"""SQLite storage for the book collection."""

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


class Database:
    """A single SQLite connection shared across request threads.

    Every operation holds a lock, which keeps the wrapper simple and safe to
    use from the ThreadingHTTPServer.
    """

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def list_books(self, author=None):
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
            return [dict(row) for row in rows]

    def get_book(self, book_id):
        with self._lock:
            return self._fetch(book_id)

    def create_book(self, book):
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) "
                "VALUES (:title, :author, :year, :isbn)",
                book,
            )
            self._conn.commit()
            return self._fetch(cur.lastrowid)

    def update_book(self, book_id, book):
        """Replace the stored fields of a book. Returns None if it doesn't exist."""
        with self._lock:
            cur = self._conn.execute(
                "UPDATE books SET title = :title, author = :author, "
                "year = :year, isbn = :isbn WHERE id = :id",
                {**book, "id": book_id},
            )
            self._conn.commit()
            if cur.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete_book(self, book_id):
        """Delete a book. Returns False if it doesn't exist."""
        with self._lock:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def _fetch(self, book_id):
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None
