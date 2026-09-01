"""SQLite storage layer for the book collection."""
import sqlite3
import threading
from typing import Any, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


class BookRepository:
    """Thread-safe repository over a SQLite database."""

    def __init__(self, path: str = "books.db"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "title": row["title"], "author": row["author"],
                "year": row["year"], "isbn": row["isbn"]}

    def create(self, title: str, author: str, year: Optional[int], isbn: Optional[str]) -> dict:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (title, author, year, isbn))
            self._conn.commit()
            return self.get(cur.lastrowid, _locked=True)

    def list(self, author: Optional[str] = None) -> list[dict]:
        with self._lock:
            if author is not None:
                rows = self._conn.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            return [self._row(r) for r in rows]

    def get(self, book_id: int, _locked: bool = False) -> Optional[dict]:
        def _do():
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return self._row(row) if row else None
        if _locked:
            return _do()
        with self._lock:
            return _do()

    def update(self, book_id: int, title: str, author: str,
               year: Optional[int], isbn: Optional[str]) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (title, author, year, isbn, book_id))
            self._conn.commit()
            if cur.rowcount == 0:
                return None
            return self.get(book_id, _locked=True)

    def delete(self, book_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()
