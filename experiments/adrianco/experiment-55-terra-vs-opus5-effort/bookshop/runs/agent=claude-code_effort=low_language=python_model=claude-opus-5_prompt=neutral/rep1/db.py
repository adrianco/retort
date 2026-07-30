"""SQLite storage layer for the book collection."""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def _fetch(conn, book_id):
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return dict(row) if row else None


def create_book(title, author, year, isbn):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        return _fetch(conn, cur.lastrowid)


def list_books(author=None):
    sql = "SELECT * FROM books"
    params = ()
    if author:
        sql += " WHERE author = ?"
        params = (author,)
    sql += " ORDER BY id"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def get_book(book_id):
    with connect() as conn:
        return _fetch(conn, book_id)


def update_book(book_id, title, author, year, isbn):
    with connect() as conn:
        cur = conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (title, author, year, isbn, book_id),
        )
        if cur.rowcount == 0:
            return None
        return _fetch(conn, book_id)


def delete_book(book_id):
    with connect() as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0
