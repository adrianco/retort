"""SQLite-backed storage and validation for the book collection."""

import sqlite3
import threading

BOOK_FIELDS = ("title", "author", "year", "isbn")


class ValidationError(ValueError):
    """Raised when book input fails validation. Carries a dict of field errors."""

    def __init__(self, errors):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def validate_book(data, partial=False):
    """Validate and normalise book input.

    With partial=False (create), title and author are required.
    With partial=True (update), only the fields present are validated.
    Returns a dict containing only the recognised fields that were supplied.
    """
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    cleaned = {}

    for field in ("title", "author"):
        if field not in data:
            if not partial:
                errors[field] = "is required"
            continue
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            errors[field] = "must be a non-empty string"
        else:
            cleaned[field] = value.strip()

    if "year" in data:
        value = data["year"]
        # bool is a subclass of int in Python; reject it explicitly.
        if value is None:
            cleaned["year"] = None
        elif isinstance(value, bool) or not isinstance(value, int) or not (0 < value <= 9999):
            errors["year"] = "must be an integer between 1 and 9999"
        else:
            cleaned["year"] = value

    if "isbn" in data:
        value = data["isbn"]
        if value is None:
            cleaned["isbn"] = None
        elif not isinstance(value, str) or not value.strip():
            errors["isbn"] = "must be a non-empty string"
        else:
            cleaned["isbn"] = value.strip()

    if errors:
        raise ValidationError(errors)
    return cleaned


class BookStore:
    """Thin repository around a SQLite database.

    A single connection is shared across threads (the HTTP server is threaded),
    so every operation is serialised with a lock.
    """

    def __init__(self, db_path=":memory:"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self):
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    title  TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year   INTEGER,
                    isbn   TEXT
                )
                """
            )

    @staticmethod
    def _row_to_dict(row):
        return {key: row[key] for key in ("id", *BOOK_FIELDS)}

    def create(self, data):
        book = validate_book(data)
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book["title"], book["author"], book.get("year"), book.get("isbn")),
            )
            new_id = cur.lastrowid
        return self.get(new_id)

    def get(self, book_id):
        with self._lock:
            row = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, author=None):
        query = "SELECT * FROM books"
        params = ()
        if author is not None:
            # Case-insensitive exact match on author.
            query += " WHERE LOWER(author) = LOWER(?)"
            params = (author.strip(),)
        query += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update(self, book_id, data):
        """Partially update a book. Returns the updated book, or None if not found."""
        changes = validate_book(data, partial=True)
        if not self.get(book_id):
            return None
        if changes:
            assignments = ", ".join(f"{field} = ?" for field in changes)
            with self._lock, self._conn:
                self._conn.execute(
                    f"UPDATE books SET {assignments} WHERE id = ?",
                    (*changes.values(), book_id),
                )
        return self.get(book_id)

    def delete(self, book_id):
        """Delete a book. Returns True if a row was removed."""
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0

    def close(self):
        with self._lock:
            self._conn.close()
