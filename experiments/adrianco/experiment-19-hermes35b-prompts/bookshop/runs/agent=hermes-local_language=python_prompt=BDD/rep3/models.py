"""
Data model and persistence layer for the Book Collection REST API.
Uses SQLite as the embedded database.
"""
import sqlite3
import os


DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db_connection():
    """Return a new SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the books table if it does not exist."""
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def insert_book(title, author, year=None, isbn=None):
    """Insert a new book and return the id of the created row."""
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn),
    )
    conn.commit()
    book_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def select_all_books(author=None):
    """Return all books, optionally filtered by author."""
    conn = get_db_connection()
    if author:
        rows = conn.execute(
            "SELECT * FROM books WHERE author = ?", (author,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def select_book_by_id(book_id):
    """Return a single book by id, or None if not found."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_dict(row)


def update_book(book_id, title=None, author=None, year=None, isbn=None):
    """Update an existing book. Returns the updated row or None if not found."""
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing is None:
        conn.close()
        return None

    t = title if title is not None else existing["title"]
    a = author if author is not None else existing["author"]
    y = year if year is not None else existing["year"]
    i = isbn if isbn is not None else existing["isbn"]

    conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (t, a, y, i, book_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def delete_book(book_id):
    """Delete a book by id. Returns True if deleted, False if not found."""
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing is None:
        conn.close()
        return False
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    return True


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
