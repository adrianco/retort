"""SQLite storage for books.

Every operation opens its own short-lived connection. SQLite connections are
cheap to open, and this keeps each connection on the thread that created it:
FastAPI runs synchronous endpoints in a thread pool, and ``sqlite3`` connections
must not be shared between threads. WAL journaling lets reads proceed while a
write is in progress.
"""

import sqlite3
import threading
import time
import unicodedata
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from books_api.schemas import Book, BookIn

#: Largest value an SQLite ``INTEGER PRIMARY KEY`` can hold (signed 64-bit).
MAX_ID = 2**63 - 1

#: How long initialize() keeps retrying while another process holds the lock.
_INIT_TIMEOUT_SECONDS = 10.0

# AUTOINCREMENT guarantees the id of a deleted book is never handed out again,
# so a stale /books/{id} URL can never start pointing at a different book.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL CHECK (title <> ''),
    author TEXT    NOT NULL CHECK (author <> ''),
    year   INTEGER,
    isbn   TEXT
)
"""

_COLUMNS = "id, title, author, year, isbn"


class DatabaseUnavailable(Exception):
    """The database cannot be used: it is missing, locked, unreadable or corrupt."""


def _fold(text: str) -> str:
    # For case-insensitive matching across all of Unicode, as SQLite's NOCASE and
    # LIKE only fold ASCII: "ÉMILE" matches "émile", "STRASSE" matches "Straße".
    # NFKC first, so an "É" typed as E plus a combining accent matches too.
    return unicodedata.normalize("NFKC", text).casefold()


class BookRepository:
    """CRUD operations on the ``books`` table of one SQLite database file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path in ("", ":memory:"):
            # Each operation opens its own connection, and each would get a
            # separate, empty temporary database.
            raise ValueError(f"a database file is required, not {self.path!r}")
        self._initialized = False
        self._init_lock = threading.Lock()

    def initialize(self) -> None:
        """Create the schema if it does not exist yet.

        Safe to call repeatedly, and from several threads or processes at once.
        """
        with self._init_lock:
            if self._initialized:
                return
            deadline = time.monotonic() + _INIT_TIMEOUT_SECONDS
            while True:
                try:
                    with closing(sqlite3.connect(self.path)) as conn:
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute(_SCHEMA)
                    break
                except sqlite3.OperationalError as exc:
                    # Switching a new database to WAL fails at once with "database
                    # is locked" while another process holds the write lock, e.g.
                    # when several server workers start together: SQLite skips its
                    # busy timeout there to avoid deadlock. So wait and retry.
                    if "locked" not in str(exc) or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
            self._initialized = True

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection whose transaction commits on success, rolls back on error.

        Raises ``DatabaseUnavailable`` if the database cannot be used.
        """
        try:
            if not self._initialized:
                self.initialize()
            conn = sqlite3.connect(self.path)
            try:
                conn.row_factory = sqlite3.Row
                conn.create_function("fold", 1, _fold, deterministic=True)
                with conn:
                    yield conn
            finally:
                conn.close()
        except sqlite3.DatabaseError as exc:
            # OperationalError (cannot open, locked, no such table) and a plain
            # DatabaseError (not a database, corrupt) are about the file. Other
            # subclasses, such as IntegrityError, mean a bug and propagate as-is.
            if isinstance(exc, sqlite3.OperationalError) or type(exc) is sqlite3.DatabaseError:
                raise DatabaseUnavailable(str(exc)) from exc
            raise

    def ping(self) -> None:
        """Raise ``DatabaseUnavailable`` unless the books table can be read."""
        with self._connect() as conn:
            conn.execute("SELECT 1 FROM books LIMIT 1").fetchone()

    def create(self, data: BookIn) -> Book:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (data.title, data.author, data.year, data.isbn),
            )
            book_id = cursor.lastrowid
        return Book(id=book_id, **data.model_dump())

    def get(self, book_id: int) -> Book | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return Book(**row) if row else None

    def list_books(self, author: str | None = None) -> list[Book]:
        """Return books in id order, optionally only those whose author contains
        ``author``, ignoring case. The filter is plain text: ``%`` and ``_`` are
        not wildcards."""
        query = f"SELECT {_COLUMNS} FROM books"
        params: tuple[str, ...] = ()
        if author:
            query += " WHERE instr(fold(author), ?) > 0"
            params = (_fold(author),)
        with self._connect() as conn:
            rows = conn.execute(query + " ORDER BY id", params).fetchall()
        return [Book(**row) for row in rows]

    def replace(self, book_id: int, data: BookIn) -> Book | None:
        """Overwrite every field of a book. Returns ``None`` if it does not exist."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (data.title, data.author, data.year, data.isbn, book_id),
            )
            found = cursor.rowcount > 0
        return Book(id=book_id, **data.model_dump()) if found else None

    def delete(self, book_id: int) -> bool:
        """Delete a book. Returns ``False`` if it did not exist."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0
