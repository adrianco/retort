"""SQLite database layer for the Book Collection API."""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")


def get_db_path():
    """Return the database file path."""
    return DB_PATH


def set_db_path(path):
    """Override the database file path."""
    global DB_PATH
    DB_PATH = path


def get_connection(db_path=None):
    """Create and return a database connection with row factory."""
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db(db_path=None):
    """Context manager for database connections.

    Yields a connection and commits on success, rolls back on exception.
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=None):
    """Initialize the database, creating the books table if it doesn't exist."""
    conn = get_connection(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT UNIQUE
            )
        """)
        conn.commit()
    finally:
        conn.close()


def create_book(title, author, year=None, isbn=None):
    """Create a new book record.

    Args:
        title: Book title (required, non-empty).
        author: Book author (required, non-empty).
        year: Publication year (optional).
        isbn: ISBN (optional).

    Returns:
        dict with id, title, author, year, isbn.

    Raises:
        ValueError: If title or author is missing/empty.
    """
    if not title or not str(title).strip():
        raise ValueError("title is required")
    if not author or not str(author).strip():
        raise ValueError("author is required")

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (str(title).strip(), str(author).strip(), year, isbn),
        )
        book_id = cursor.lastrowid
        row = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        return _row_to_dict(row)


def get_book_by_id(book_id):
    """Retrieve a single book by ID.

    Returns:
        dict with id, title, author, year, isbn, or None if not found.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_books(author=None):
    """List all books, optionally filtered by author.

    Args:
        author: Optional author name to filter by (case-insensitive).

    Returns:
        list of dicts with id, title, author, year, isbn.
    """
    with get_db() as conn:
        if author:
            rows = conn.execute(
                "SELECT id, title, author, year, isbn FROM books "
                "WHERE LOWER(author) = LOWER(?)",
                (author,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, author, year, isbn FROM books"
            ).fetchall()
    return [_row_to_dict(row) for row in rows]


def update_book(book_id, title=None, author=None, year=None, isbn=None):
    """Update an existing book.

    Only provided fields are updated. Title and author must be non-empty if provided.

    Args:
        book_id: ID of the book to update.
        title: New title (optional, required if provided).
        author: New author (optional, required if provided).
        year: New year (optional).
        isbn: New ISBN (optional).

    Returns:
        dict with updated book data, or None if book not found.

    Raises:
        ValueError: If title or author is provided but empty.
    """
    if title is not None:
        if not str(title).strip():
            raise ValueError("title is required")
        title = str(title).strip()
    if author is not None:
        if not str(author).strip():
            raise ValueError("author is required")
        author = str(author).strip()

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        if existing is None:
            return None

        current = _row_to_dict(existing)
        new_title = title if title is not None else current["title"]
        new_author = author if author is not None else current["author"]
        new_year = year if year is not None else current["year"]
        new_isbn = isbn if isbn is not None else current["isbn"]

        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (new_title, new_author, new_year, new_isbn, book_id),
        )
        row = conn.execute(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        return _row_to_dict(row)


def delete_book(book_id):
    """Delete a book by ID.

    Args:
        book_id: ID of the book to delete.

    Returns:
        True if deleted, False if not found.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM books WHERE id = ?", (book_id,)
        )
        return cursor.rowcount > 0


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }
