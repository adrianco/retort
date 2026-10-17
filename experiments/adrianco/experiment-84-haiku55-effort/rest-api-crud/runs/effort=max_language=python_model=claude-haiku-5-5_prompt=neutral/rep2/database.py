"""SQLite persistence for books.

Functions take an open connection, so the caller decides how long it lives.
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
)
"""

COLUMNS = "id, title, author, year, isbn"


def _casefold(value: str | None) -> str | None:
    return None if value is None else value.casefold()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # SQLite's lower() only folds ASCII. casefold() also handles accented names.
    conn.create_function("casefold", 1, _casefold, deterministic=True)
    return conn


def init_db(path: str) -> None:
    conn = connect(path)
    try:
        with conn:
            conn.execute(SCHEMA)
    finally:
        conn.close()


def ping(conn: sqlite3.Connection) -> None:
    """Raise sqlite3.Error unless the books table can be read."""
    conn.execute("SELECT 1 FROM books LIMIT 1").fetchone()


def insert_book(conn: sqlite3.Connection, book: dict) -> dict:
    with conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) "
            "VALUES (:title, :author, :year, :isbn)",
            book,
        )
    return {"id": cursor.lastrowid, **book}


def get_book(conn: sqlite3.Connection, book_id: int) -> dict | None:
    row = conn.execute(
        f"SELECT {COLUMNS} FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return None if row is None else dict(row)


def list_books(conn: sqlite3.Connection, author: str | None = None) -> list[dict]:
    if author is None:
        rows = conn.execute(f"SELECT {COLUMNS} FROM books ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            f"SELECT {COLUMNS} FROM books "
            "WHERE instr(casefold(author), casefold(?)) > 0 ORDER BY id",
            (author,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_book(conn: sqlite3.Connection, book_id: int, book: dict) -> dict | None:
    with conn:
        cursor = conn.execute(
            "UPDATE books SET title = :title, author = :author, "
            "year = :year, isbn = :isbn WHERE id = :id",
            {**book, "id": book_id},
        )
    return {"id": book_id, **book} if cursor.rowcount else None


def delete_book(conn: sqlite3.Connection, book_id: int) -> bool:
    with conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return cursor.rowcount > 0
