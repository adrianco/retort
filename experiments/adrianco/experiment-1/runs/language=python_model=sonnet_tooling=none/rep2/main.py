import sqlite3
import contextlib
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, field_validator

DATABASE = "books.db"

app = FastAPI(title="Book Collection API")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with contextlib.closing(get_db()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
        """)
        conn.commit()


init_db()


class BookCreate(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("must not be empty")
        return v.strip() if v is not None else v


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    with contextlib.closing(get_db()) as conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        conn.commit()
        book_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return row_to_dict(row)


@app.get("/books")
def list_books(author: Optional[str] = Query(default=None)):
    with contextlib.closing(get_db()) as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author LIKE ?", (f"%{author}%",)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books").fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    with contextlib.closing(get_db()) as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row_to_dict(row)


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookUpdate):
    fields = {k: v for k, v in book.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [book_id]
    with contextlib.closing(get_db()) as conn:
        result = conn.execute(
            f"UPDATE books SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Book not found")
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return row_to_dict(row)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with contextlib.closing(get_db()) as conn:
        result = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Book not found")
