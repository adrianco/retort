import sqlite3
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

app = FastAPI(title="Book API", version="1.0.0")

# Database setup
DATABASE = "books.db"

def init_db():
    """Initialize the database with the books table."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Data models
class Book(BaseModel):
    id: Optional[int] = None
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

class BookCreate(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

# Initialize database
init_db()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/books", response_model=List[Book])
async def get_books(author: Optional[str] = None):
    """Get all books, optionally filtered by author."""
    conn = get_db_connection()
    
    if author:
        query = "SELECT * FROM books WHERE author LIKE ?"
        books = conn.execute(query, (f"%{author}",)).fetchall()
    else:
        query = "SELECT * FROM books"
        books = conn.execute(query).fetchall()
    
    conn.close()
    return [dict(book) for book in books]

@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int):
    """Get a single book by ID."""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
    return dict(book)

@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate):
    """Create a new book."""
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN must be unique")
    except sqlite3.Error as e:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data")
    
    conn.close()
    return {"id": book_id, "title": book.title, "author": book.author, "year": book.year, "isbn": book.isbn}

@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book: BookUpdate):
    """Update a book by ID."""
    conn = get_db_connection()
    
    # Check if book exists
    existing_book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing_book is None:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,详情="Book not found")
    
    # Build dynamic update query
    update_fields = []
    update_values = []
    for field, value in book.dict().items():
        if value is not None:
            update_fields.append(f"{field} = ?")
            update_values.append(value)
    
    if not update_fields:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided for update")
    
    update_query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(book_id)
    
    try:
        conn.execute(update_query, update_values)
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN must be unique")
    except sqlite3.Error as e:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data")
    
    updated_book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return dict(updated_book)

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int):
    """Delete a book by ID."""
    conn = get_db_connection()
    
    # Check if book exists
    existing_book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing_book is None:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return None