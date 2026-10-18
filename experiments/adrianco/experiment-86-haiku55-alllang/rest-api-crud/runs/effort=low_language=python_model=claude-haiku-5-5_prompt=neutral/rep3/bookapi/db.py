"""SQLite-backed storage for the book collection."""

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
)
"""


class IsbnConflictError(Exception):
    """Raised when another book already uses the requested ISBN."""


class BookStore:
    """Thread-safe wrapper around a single SQLite connection."""

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

    def create(self, book):
        with self._lock:
            try:
                cur = self._conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    (book["title"], book["author"], book.get("year"), book.get("isbn")),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                raise IsbnConflictError(book.get("isbn")) from exc
            return self._fetch(cur.lastrowid)

    def get(self, book_id):
        with self._lock:
            return self._fetch(book_id)

    def list(self, author=None):
        with self._lock:
            if author is None:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                ).fetchall()
            return [dict(row) for row in rows]

    def update(self, book_id, book):
        with self._lock:
            try:
                cur = self._conn.execute(
                    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                    (book["title"], book["author"], book.get("year"), book.get("isbn"), book_id),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                raise IsbnConflictError(book.get("isbn")) from exc
            if cur.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete(self, book_id):
        with self._lock:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def _fetch(self, book_id):
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None
