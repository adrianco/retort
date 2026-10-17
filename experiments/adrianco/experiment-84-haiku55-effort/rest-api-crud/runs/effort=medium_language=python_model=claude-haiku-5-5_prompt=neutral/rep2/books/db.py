"""SQLite-backed storage for the book collection."""

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT    UNIQUE
)
"""


class DuplicateISBNError(Exception):
    """Raised when a book's ISBN is already used by another book."""


class BookStore:
    def __init__(self, path=":memory:"):
        # One shared connection guarded by a lock: safe for the threaded server
        # and works for in-memory databases, which are per-connection.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    def close(self):
        self._conn.close()

    def ping(self):
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, data):
        with self._lock:
            cur = self._write(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data["title"], data["author"], data["year"], data["isbn"]),
                data["isbn"],
            )
            return self._fetch(cur.lastrowid)

    def get(self, book_id):
        with self._lock:
            return self._fetch(book_id)

    def list_books(self, author=None):
        sql = "SELECT * FROM books"
        params = ()
        if author is not None:
            sql += " WHERE author = ? COLLATE NOCASE"
            params = (author,)
        sql += " ORDER BY id"
        with self._lock:
            return [dict(row) for row in self._conn.execute(sql, params)]

    def update(self, book_id, data):
        with self._lock:
            cur = self._write(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data["title"], data["author"], data["year"], data["isbn"], book_id),
                data["isbn"],
            )
            if cur.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete(self, book_id):
        with self._lock:
            cur = self._write("DELETE FROM books WHERE id = ?", (book_id,), None)
            return cur.rowcount > 0

    def _write(self, sql, params, isbn):
        # Caller must hold self._lock.
        try:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur
        except sqlite3.IntegrityError as exc:
            self._conn.rollback()
            # The only UNIQUE constraint is on isbn, and NOT NULL fields are
            # guaranteed by validation before we get here.
            raise DuplicateISBNError(isbn) from exc

    def _fetch(self, book_id):
        # Caller must hold self._lock.
        row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row is not None else None
