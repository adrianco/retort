"""Book collection REST API (FastAPI + SQLite)."""

import os
import sqlite3
from contextlib import asynccontextmanager, closing
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

def db_path() -> str:
    """Resolved at call time so tests can point BOOKS_DB at a temp file."""
    return os.environ.get("BOOKS_DB", "books.db")


def connect(path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str = None) -> None:
    with closing(connect(path)) as conn:
        conn.execute(
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
        conn.commit()


def get_db():
    with closing(connect()) as conn:
        yield conn


class BookIn(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("year")
    @classmethod
    def sane_year(cls, v):
        if v is not None and not (0 < v <= 2200):
            raise ValueError("year out of range")
        return v


class Book(BookIn):
    id: int


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookIn, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn),
    )
    db.commit()
    return Book(id=cur.lastrowid, **book.model_dump())


@app.get("/books", response_model=list[Book])
def list_books(
    author: Optional[str] = Query(None),
    db: sqlite3.Connection = Depends(get_db),
):
    if author:
        rows = db.execute(
            "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return [Book(**dict(r)) for r in rows]


def _fetch(db, book_id: int):
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, db: sqlite3.Connection = Depends(get_db)):
    return Book(**dict(_fetch(db, book_id)))


@app.put("/books/{book_id}", response_model=Book)
def update_book(
    book_id: int, book: BookIn, db: sqlite3.Connection = Depends(get_db)
):
    _fetch(db, book_id)
    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (book.title, book.author, book.year, book.isbn, book_id),
    )
    db.commit()
    return Book(id=book_id, **book.model_dump())


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: sqlite3.Connection = Depends(get_db)):
    _fetch(db, book_id)
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return JSONResponse(status_code=204, content=None)
