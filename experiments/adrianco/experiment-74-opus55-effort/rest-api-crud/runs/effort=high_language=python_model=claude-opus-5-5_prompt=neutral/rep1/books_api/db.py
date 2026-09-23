"""SQLite persistence for books."""

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""

COLUMNS = ("id", "title", "author", "year", "isbn")


class DuplicateIsbnError(Exception):
    """Raised when a book with the same ISBN already exists."""


class BookRepository:
    """Thread-safe CRUD access to the books table.

    A single connection is shared and guarded by a lock so that ``:memory:``
    databases work and concurrent requests from a threaded server are safe.
    """

    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self):
        with self._lock:
            self._conn.close()

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, book):
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                        (book["title"], book["author"], book.get("year"), book.get("isbn")),
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateIsbnError(book.get("isbn")) from exc
            return self._get_locked(cur.lastrowid)

    def list(self, author=None):
        query = "SELECT id, title, author, year, isbn FROM books"
        params = ()
        if author is not None:
            query += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        query += " ORDER BY id"
        with self._lock:
            return [dict(row) for row in self._conn.execute(query, params)]

    def get(self, book_id):
        with self._lock:
            return self._get_locked(book_id)

    def update(self, book_id, book):
        with self._lock:
            try:
                with self._conn:
                    cur = self._conn.execute(
                        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                        (book["title"], book["author"], book.get("year"), book.get("isbn"), book_id),
                    )
            except sqlite3.IntegrityError as exc:
                raise DuplicateIsbnError(book.get("isbn")) from exc
            if cur.rowcount == 0:
                return None
            return self._get_locked(book_id)

    def delete(self, book_id):
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def _get_locked(self, book_id):
        row = self._conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None
