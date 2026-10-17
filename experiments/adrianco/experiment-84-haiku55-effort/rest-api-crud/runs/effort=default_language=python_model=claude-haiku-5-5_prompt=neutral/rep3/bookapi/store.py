"""SQLite-backed storage for books."""

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

COLUMNS = "id, title, author, year, isbn"


class BookStore:
    """Thin repository over a single SQLite connection.

    The connection is shared across request threads, so every operation holds
    ``self._lock``. Pass ``":memory:"`` for an ephemeral database.
    """

    def __init__(self, path: str = "books.db"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def ping(self) -> None:
        """Raise if the database is unreachable."""
        with self._lock:
            self._conn.execute("SELECT 1").fetchone()

    def create(self, book: dict) -> dict:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book["year"], book["isbn"]),
            )
            return self._fetch(cur.lastrowid)

    def get(self, book_id: int) -> dict | None:
        with self._lock:
            return self._fetch(book_id)

    def list(self, author: str | None = None) -> list[dict]:
        """Return all books ordered by id. ``author`` is an exact, case-insensitive match."""
        with self._lock:
            if author is None:
                rows = self._conn.execute(f"SELECT {COLUMNS} FROM books ORDER BY id")
            else:
                rows = self._conn.execute(
                    f"SELECT {COLUMNS} FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                    (author,),
                )
            return [dict(row) for row in rows.fetchall()]

    def update(self, book_id: int, book: dict) -> dict | None:
        """Replace all fields of a book. Returns ``None`` if it does not exist."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book["title"], book["author"], book["year"], book["isbn"], book_id),
            )
            if cur.rowcount == 0:
                return None
            return self._fetch(book_id)

    def delete(self, book_id: int) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cur.rowcount > 0

    def _fetch(self, book_id: int) -> dict | None:
        row = self._conn.execute(
            f"SELECT {COLUMNS} FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None
