"""FastAPI application exposing a REST API for a book collection."""

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, status

from . import db
from .models import Book, BookCreate, BookUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


def _row_to_book(row) -> Book:
    return Book(
        id=row["id"],
        title=row["title"],
        author=row["author"],
        year=row["year"],
        isbn=row["isbn"],
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate) -> Book:
    with db.get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
    return _row_to_book(row)


@app.get("/books", response_model=List[Book])
def list_books(author: Optional[str] = Query(None)) -> List[Book]:
    with db.get_connection() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [_row_to_book(r) for r in rows]


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int) -> Book:
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return _row_to_book(row)


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate) -> Book:
    with db.get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book.title, book.author, book.year, book.isbn, book_id),
        )
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_book(row)


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int) -> None:
    with db.get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return None
