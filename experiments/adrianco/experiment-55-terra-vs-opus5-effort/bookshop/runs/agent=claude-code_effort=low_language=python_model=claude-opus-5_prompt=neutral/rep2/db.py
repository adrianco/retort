"""SQLite persistence layer for the book collection."""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


def connect(database):
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    with conn:
        conn.executescript(SCHEMA)


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_book(conn, data):
    with conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
    return get_book(conn, cur.lastrowid)


def list_books(conn, author=None):
    if author:
        # Case-insensitive exact match on author.
        rows = conn.execute(
            "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
            (author,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


def get_book(conn, book_id):
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return row_to_dict(row) if row else None


def update_book(conn, book_id, data):
    if get_book(conn, book_id) is None:
        return None
    with conn:
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (data["title"], data["author"], data.get("year"), data.get("isbn"), book_id),
        )
    return get_book(conn, book_id)


def delete_book(conn, book_id):
    with conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cur.rowcount > 0
