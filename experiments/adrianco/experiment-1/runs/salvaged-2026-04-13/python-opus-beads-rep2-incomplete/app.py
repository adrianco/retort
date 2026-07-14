import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("BOOKS_DB", "books.db")


def get_db_path() -> str:
    return os.environ.get("BOOKS_DB", DB_PATH)


@contextmanager
def get_conn():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
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


class BookIn(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class Book(BookIn):
    id: int


app = FastAPI(title="Books API")


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookIn):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        book_id = cur.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_book(row)


@app.get("/books")
def list_books(author: Optional[str] = Query(None)):
    with get_conn() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [_row_to_book(r) for r in rows]


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return _row_to_book(row)


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")
        merged = {
            "title": book.title if book.title is not None else existing["title"],
            "author": book.author if book.author is not None else existing["author"],
            "year": book.year if book.year is not None else existing["year"],
            "isbn": book.isbn if book.isbn is not None else existing["isbn"],
        }
        conn.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
        )
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_book(row)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return None
