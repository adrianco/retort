"""SQLite persistence layer for the book collection service."""

import sqlite3
from contextlib import contextmanager

DEFAULT_DB_PATH = "books.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT NOT NULL,
    author  TEXT NOT NULL,
    year    INTEGER,
    isbn    TEXT
)
"""


class Database:
    """Thin wrapper around a SQLite connection holding the books table."""

    def __init__(self, path: str = DEFAULT_DB_PATH):
        self.path = path
        # check_same_thread=False so the connection can be shared across the
        # threads FastAPI/uvicorn may use to serve requests.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    @contextmanager
    def _cursor(self):
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def create_book(self, title, author, year=None, isbn=None):
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn),
            )
            return self.get_book(cur.lastrowid)

    def list_books(self, author=None):
        with self._cursor() as cur:
            if author is not None:
                cur.execute("SELECT * FROM books WHERE author = ?", (author,))
            else:
                cur.execute("SELECT * FROM books")
            return [dict(row) for row in cur.fetchall()]

    def get_book(self, book_id):
        with self._cursor() as cur:
            cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_book(self, book_id, title, author, year=None, isbn=None):
        with self._cursor() as cur:
            cur.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (title, author, year, isbn, book_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get_book(book_id)

    def delete_book(self, book_id):
        with self._cursor() as cur:
            cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def close(self):
        self._conn.close()
