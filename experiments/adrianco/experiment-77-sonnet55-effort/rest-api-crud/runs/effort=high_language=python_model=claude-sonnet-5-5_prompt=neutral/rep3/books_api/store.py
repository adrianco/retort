"""SQLite persistence for books."""

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


class DuplicateISBN(Exception):
    """Raised when an ISBN is already used by another book."""


class BookStore:
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
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def _write(self, sql, params):
        """Run a write statement; returns the cursor. Maps ISBN clashes."""
        with self._lock:
            try:
                cur = self._conn.execute(sql, params)
                self._conn.commit()
                return cur
            except sqlite3.IntegrityError as exc:
                self._conn.rollback()
                if "isbn" in str(exc).lower():
                    raise DuplicateISBN(params[3]) from exc
                raise

    def create(self, title, author, year, isbn):
        cur = self._write(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        return self.get(cur.lastrowid)

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return dict(row) if row else None

    def list(self, author=None):
        sql, params = "SELECT * FROM books", ()
        if author is not None:
            sql, params = sql + " WHERE author = ? COLLATE NOCASE", (author,)
        with self._lock:
            rows = self._conn.execute(sql + " ORDER BY id", params).fetchall()
        return [dict(r) for r in rows]

    def update(self, book_id, title, author, year, isbn):
        cur = self._write(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        return self.get(book_id) if cur.rowcount else None

    def delete(self, book_id):
        cur = self._write("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0
