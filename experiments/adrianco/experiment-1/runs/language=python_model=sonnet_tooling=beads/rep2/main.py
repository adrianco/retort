from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, field_validator
from typing import Optional
from database import init_db, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Book Collection API", lifespan=lifespan)


class BookCreate(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author", mode="before")
    @classmethod
    def not_empty(cls, v):
        if v is not None and not str(v).strip():
            raise ValueError("must not be blank")
        return v.strip() if isinstance(v, str) else v


def row_to_dict(row) -> dict:
    return dict(row)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    with db() as conn:
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn),
        )
        book_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return row_to_dict(row)


@app.get("/books")
def list_books(author: Optional[str] = Query(default=None)):
    with db() as conn:
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author LIKE ?", (f"%{author}%",)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books").fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row_to_dict(row)


@app.put("/books/{book_id}")
def update_book(book_id: int, updates: BookUpdate):
    fields = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [book_id]
    with db() as conn:
        conn.execute(f"UPDATE books SET {set_clause} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return row_to_dict(row)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with db() as conn:
        result = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Book not found")
