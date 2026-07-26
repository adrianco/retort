"""All SQL used by the service lives here.

Keeping the queries in one place keeps the HTTP layer free of persistence
details and makes it obvious that every value reaches SQLite as a bound
parameter rather than as interpolated text.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from .errors import ConflictError
from .models import Book
from .utils import utcnow_iso

#: Columns that ``GET /books?sort=`` is allowed to order by.
SORTABLE_FIELDS = ("id", "title", "author", "year", "created_at", "updated_at")

#: SQLite stores integers as signed 64-bit values; anything outside this range
#: cannot be bound as a parameter at all.
SQLITE_INT_MIN = -(2 ** 63)
SQLITE_INT_MAX = 2 ** 63 - 1


def is_storable_int(value: int) -> bool:
    """True when SQLite is able to bind ``value`` as an INTEGER."""
    return SQLITE_INT_MIN <= value <= SQLITE_INT_MAX

_SELECT = (
    "SELECT id, title, author, year, isbn, created_at, updated_at FROM books"
)


class BookRepository:
    """Data access for the ``books`` table."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get(self, book_id: int) -> Optional[Book]:
        if not is_storable_int(book_id):
            return None  # no row can carry an id SQLite cannot even store
        row = self._connection.execute(
            _SELECT + " WHERE id = ?", (book_id,)
        ).fetchone()
        return Book.from_row(row) if row is not None else None

    def list(
        self,
        *,
        author: Optional[str] = None,
        year: Optional[int] = None,
        query: Optional[str] = None,
        sort: Tuple[str, str] = ("id", "ASC"),
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Book]:
        where, params = self._where(author=author, year=year, query=query)
        sql = _SELECT + where + " ORDER BY " + self._order_by(sort)
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params = list(params) + [limit, offset]
        elif offset:
            # SQLite requires a LIMIT before an OFFSET; -1 means "no limit".
            sql += " LIMIT -1 OFFSET ?"
            params = list(params) + [offset]
        rows = self._connection.execute(sql, params).fetchall()
        return [Book.from_row(row) for row in rows]

    def count(
        self,
        *,
        author: Optional[str] = None,
        year: Optional[int] = None,
        query: Optional[str] = None,
    ) -> int:
        where, params = self._where(author=author, year=year, query=query)
        row = self._connection.execute(
            "SELECT COUNT(*) AS total FROM books" + where, params
        ).fetchone()
        return int(row["total"])

    def total(self) -> int:
        """Number of books stored, ignoring any filter."""
        return self.count()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    def create(self, fields: Dict[str, Any]) -> Book:
        now = utcnow_iso()
        with self._integrity_guard():
            cursor = self._connection.execute(
                """
                INSERT INTO books
                    (title, author, year, isbn, isbn_normalized, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields["title"],
                    fields["author"],
                    fields.get("year"),
                    fields.get("isbn"),
                    fields.get("isbn_normalized"),
                    now,
                    now,
                ),
            )
            self._connection.commit()
        # The inserted row is fully known here, so there is no need to read it
        # back — and no window in which the follow-up query could fail.
        return Book(
            id=int(cursor.lastrowid),
            title=fields["title"],
            author=fields["author"],
            year=fields.get("year"),
            isbn=fields.get("isbn"),
            created_at=now,
            updated_at=now,
        )

    def replace(self, book_id: int, fields: Dict[str, Any]) -> Optional[Book]:
        """Overwrite every mutable column of a book (``PUT`` semantics)."""
        if not is_storable_int(book_id):
            return None
        with self._integrity_guard():
            cursor = self._connection.execute(
                """
                UPDATE books
                   SET title = ?, author = ?, year = ?, isbn = ?,
                       isbn_normalized = ?, updated_at = ?
                 WHERE id = ?
                """,
                (
                    fields["title"],
                    fields["author"],
                    fields.get("year"),
                    fields.get("isbn"),
                    fields.get("isbn_normalized"),
                    utcnow_iso(),
                    book_id,
                ),
            )
            self._connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get(book_id)

    def update(self, book_id: int, fields: Dict[str, Any]) -> Optional[Book]:
        """Overwrite only the supplied columns (``PATCH`` semantics)."""
        if not is_storable_int(book_id):
            return None
        columns = [key for key in ("title", "author", "year", "isbn", "isbn_normalized") if key in fields]
        if not columns:
            return self.get(book_id)
        assignments = ", ".join("{} = ?".format(column) for column in columns)
        params: List[Any] = [fields[column] for column in columns]
        params.append(utcnow_iso())
        params.append(book_id)
        with self._integrity_guard():
            cursor = self._connection.execute(
                "UPDATE books SET {}, updated_at = ? WHERE id = ?".format(assignments),
                params,
            )
            self._connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get(book_id)

    def delete(self, book_id: int) -> bool:
        if not is_storable_int(book_id):
            return False
        cursor = self._connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self._connection.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _where(
        *,
        author: Optional[str],
        year: Optional[int],
        query: Optional[str],
    ) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if author:
            clauses.append("author = ? COLLATE NOCASE")
            params.append(author)
        if year is not None:
            clauses.append("year = ?")
            params.append(year)
        if query:
            clauses.append("(title LIKE ? ESCAPE '\\' OR author LIKE ? ESCAPE '\\')")
            pattern = "%{}%".format(_escape_like(query))
            params.extend([pattern, pattern])
        if not clauses:
            return "", params
        return " WHERE " + " AND ".join(clauses), params

    @staticmethod
    def _order_by(sort: Tuple[str, str]) -> str:
        column, direction = sort
        if column not in SORTABLE_FIELDS:  # pragma: no cover - guarded by validation
            raise ValueError("unsupported sort column: {!r}".format(column))
        direction = "DESC" if direction.upper() == "DESC" else "ASC"
        collation = " COLLATE NOCASE" if column in ("title", "author") else ""
        order = "{}{} {}".format(column, collation, direction)
        if column != "id":
            order += ", id ASC"  # keep paging stable when values tie
        return order

    class _IntegrityGuard:
        """Roll back a failed write and translate constraint failures."""

        def __init__(self, connection: sqlite3.Connection) -> None:
            self._connection = connection

        def __enter__(self) -> "BookRepository._IntegrityGuard":
            return self

        def __exit__(self, exc_type, exc, traceback):
            if exc_type is None:
                return False
            # Never leave a half-finished transaction behind, whatever failed.
            self._connection.rollback()
            if not issubclass(exc_type, sqlite3.IntegrityError):
                return False
            if "isbn" in str(exc):
                raise ConflictError(
                    "Another book already uses this ISBN.",
                    details={"isbn": "Must be unique across the collection."},
                ) from exc
            # Validation should have caught anything else, so let it surface as
            # a logged 500 rather than echoing SQL back to the client.
            return False

    def _integrity_guard(self) -> "BookRepository._IntegrityGuard":
        return self._IntegrityGuard(self._connection)


def _escape_like(value: str) -> str:
    """Escape the wildcards of a ``LIKE`` pattern supplied by a client."""
    for character in ("\\", "%", "_"):
        value = value.replace(character, "\\" + character)
    return value


__all__ = [
    "BookRepository",
    "SORTABLE_FIELDS",
    "SQLITE_INT_MAX",
    "SQLITE_INT_MIN",
    "is_storable_int",
]
