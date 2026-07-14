"""Book Collection REST API — FastAPI + SQLite."""

import sqlite3
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# SQLite setup
# ---------------------------------------------------------------------------
def _get_db_path():
    return os.environ.get("BOOK_DB", "books.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the books table if it doesn't exist."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()

app = FastAPI(title="Book Collection API")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: int | None = None
    isbn: str | None = None


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    author: str | None = Field(None, min_length=1)
    year: int | None = None
    isbn: str | None = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    year: int | None
    isbn: str | None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    now = datetime.utcnow().isoformat()
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO books "
            "(title, author, year, isbn, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn, now, now),
        )
        conn.commit()
        book_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return BookResponse(**row_to_dict(row))
    finally:
        conn.close()


@app.get("/books")
def list_books(author: str | None = Query(None)):
    conn = get_db()
    try:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [BookResponse(**row_to_dict(r)) for r in rows]
    finally:
        conn.close()


@app.get("/books/{book_id}")
def get_book(book_id: int):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookResponse(**row_to_dict(row))
    finally:
        conn.close()


@app.put("/books/{book_id}")
def update_book(book_id: int, update: BookUpdate):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")

        existing_dict = row_to_dict(existing)
        update_dict = update.model_dump(exclude_unset=True)

        for key, val in update_dict.items():
            existing_dict[key] = val
        existing_dict["updated_at"] = datetime.utcnow().isoformat()

        conn.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=? WHERE id=?",
            (
                existing_dict["title"],
                existing_dict["author"],
                existing_dict["year"],
                existing_dict["isbn"],
                existing_dict["updated_at"],
                book_id,
            ),
        )
        conn.commit()

        updated = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return BookResponse(**row_to_dict(updated))
    finally:
        conn.close()


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
    finally:
        conn.close()
