#!/usr/bin/env python3
"""Book Collection REST API Service."""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3
import os

app = FastAPI(title="Book Collection API")

# Database setup
DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the books table."""
    conn = get_db_connection()
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
    conn.close()

# Pydantic models
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Book title (required)")
    author: str = Field(..., min_length=1, description="Author name (required)")
    year: Optional[int] = Field(None, ge=1000, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN number")

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="Book title")
    author: Optional[str] = Field(None, min_length=1, description="Author name")
    year: Optional[int] = Field(None, ge=1000, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN number")

class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]

class BooksList(BaseModel):
    books: List[Book]
    total: int

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# Get all books with optional author filter
@app.get("/books", response_model=BooksList)
async def list_books(author: Optional[str] = Query(None, description="Filter by author name")):
    """List all books, optionally filtered by author."""
    conn = get_db_connection()
    if author:
        books = conn.execute(
            "SELECT * FROM books WHERE author LIKE ?",
            (f"%{author}%",)
        ).fetchall()
    else:
        books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    
    book_list = [dict(book) for book in books]
    return {"books": book_list, "total": len(book_list)}

# Get single book by ID
@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int):
    """Get a single book by ID."""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return dict(book)

# Create a new book
@app.post("/books", response_model=Book, status_code=201)
async def create_book(book: BookCreate):
    """Create a new book."""
    # Validate required fields
    if not book.title or not book.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if not book.author or not book.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title.strip(), book.author.strip(), book.year, book.isbn)
    )
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    
    return {
        "id": book_id,
        "title": book.title.strip(),
        "author": book.author.strip(),
        "year": book.year,
        "isbn": book.isbn
    }

# Update a book
@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book: BookUpdate):
    """Update a book."""
    # Check if book exists
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Build update query
    update_fields = []
    values = []
    
    if book.title is not None:
        if not book.title.strip():
            conn.close()
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        update_fields.append("title = ?")
        values.append(book.title.strip())
    
    if book.author is not None:
        if not book.author.strip():
            conn.close()
            raise HTTPException(status_code=400, detail="Author cannot be empty")
        update_fields.append("author = ?")
        values.append(book.author.strip())
    
    if book.year is not None:
        update_fields.append("year = ?")
        values.append(book.year)
    
    if book.isbn is not None:
        update_fields.append("isbn = ?")
        values.append(book.isbn)
    
    if update_fields:
        values.append(book_id)
        query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
        conn.execute(query, values)
        conn.commit()
    
    # Fetch updated book
    updated = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    
    return dict(updated)

# Delete a book
@app.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int):
    """Delete a book."""
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    conn.close()
    return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
