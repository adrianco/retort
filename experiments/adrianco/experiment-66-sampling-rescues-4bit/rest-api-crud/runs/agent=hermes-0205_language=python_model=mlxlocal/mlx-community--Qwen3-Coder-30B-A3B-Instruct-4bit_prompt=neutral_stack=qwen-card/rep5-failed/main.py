import sqlite3
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

app = FastAPI()

# Database setup
DATABASE = "books.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    """)
    conn.commit()
    conn.close()

class BookBase(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: int

# Initialize database
init_db()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/books", response_model=List[Book])
def get_books(author: Optional[str] = None):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if author:
        cursor.execute("SELECT * FROM books WHERE author = ?", (author,))
    else:
        cursor.execute("SELECT * FROM books")
    
    rows = cursor.fetchall()
    conn.close()
    
    books = []
    for row in rows:
        book = Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])
        books.append(book)
    
    return books

@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])

@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Validate required fields
    if not book.title or not book.author:
        raise HTTPException(status_code=400, detail="Title and author are required")
    
    cursor.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn)
    )
    
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    
    return Book(id=book_id, title=book.title, author=book.author, year=book.year, isbn=book.isbn)

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, updated_book: BookCreate):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Update book
    cursor.execute(
        "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
        (updated_book.title, updated_book.author, updated_book.year, updated_book.isbn, book_id)
    )
    
    conn.commit()
    conn.close()
    
    return Book(id=book_id, title=updated_book.title, author=updated_book.author, year=updated_book.year, isbn=updated_book.isbn)

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()