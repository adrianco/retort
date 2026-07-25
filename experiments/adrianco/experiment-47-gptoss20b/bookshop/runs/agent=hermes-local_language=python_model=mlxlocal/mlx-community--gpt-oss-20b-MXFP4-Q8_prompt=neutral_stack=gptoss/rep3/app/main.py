from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import sqlite3
import os
from contextlib import asynccontextmanager

DATABASE = os.getenv('BOOKS_DB_PATH', os.path.join(os.path.dirname(__file__), 'books.db'))

# ---------- Database utilities ----------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );
        """
    )
    conn.commit()
    conn.close()

# Use lifespan context manager to initialize DB on startup
@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(lifespan=lifespan, title="Book Collection API")

# ---------- Pydantic models ----------
class BookBase(BaseModel):
    title: str = Field(..., example="The Hobbit")
    author: str = Field(..., example="J.R.R. Tolkien")
    year: int | None = Field(None, example=1937)
    isbn: str | None = Field(None, example="978-0547928227")

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: int

    class Config:
        orm_mode = True

# ---------- CRUD endpoints ----------
@app.post("/books", response_model=Book, status_code=201)
async def create_book(book: BookCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn),
    )
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    return Book(id=book_id, **book.dict())

@app.get("/books", response_model=list[Book])
async def list_books(author: str | None = Query(None, description="Filter by author")):
    conn = get_db_connection()
    cursor = conn.cursor()
    if author:
        cursor.execute("SELECT * FROM books WHERE author = ?", (author,))
    else:
        cursor.execute("SELECT * FROM books")
    rows = cursor.fetchall()
    conn.close()
    return [Book(**dict(row)) for row in rows]

@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return Book(**dict(row))

@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book: BookCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    cursor.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (book.title, book.author, book.year, book.isbn, book_id),
    )
    conn.commit()
    conn.close()
    return Book(id=book_id, **book.dict())

@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    conn.commit()
    conn.close()
    return JSONResponse(status_code=204, content={})

# ---------- Health check ----------
@app.get("/health")
async def health_check():
    return JSONResponse(status_code=200, content={"status": "ok"})
