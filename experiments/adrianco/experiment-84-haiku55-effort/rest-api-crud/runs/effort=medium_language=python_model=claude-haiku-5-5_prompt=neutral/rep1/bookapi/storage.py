"""SQLite-backed persistence for the book collection."""

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

FIELDS = ("title", "author", "year", "isbn")


class BookStore:
    """Thread-safe wrapper around a SQLite connection.

    Pass ``":memory:"`` (the default) for an ephemeral database, or a file path
    to persist data between runs.
    """

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        """Run a trivial query; raises if the database is unusable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, data):
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                tuple(data[f] for f in FIELDS),
            )
            self._conn.commit()
            return self._get(cur.lastrowid)

    def get(self, book_id):
        with self._lock:
            return self._get(book_id)

    def list(self, author=None):
        """Return all books, optionally filtered by a case-insensitive exact author match."""
        query = "SELECT * FROM books"
        params = ()
        if author is not None:
            query += " WHERE LOWER(author) = LOWER(?)"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]

    def update(self, book_id, data):
        """Replace all fields of a book. Returns the updated book, or None if missing."""
        with self._lock:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                tuple(data[f] for f in FIELDS) + (book_id,),
            )
            self._conn.commit()
            if cur.rowcount == 0:
                return None
            return self._get(book_id)

    def delete(self, book_id):
        """Delete a book. Returns True if a row was removed."""
        with self._lock:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def _get(self, book_id):
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_dict(row) if row is not None else None


def _row_to_dict(row):
    return {"id": row["id"], **{f: row[f] for f in FIELDS}}
