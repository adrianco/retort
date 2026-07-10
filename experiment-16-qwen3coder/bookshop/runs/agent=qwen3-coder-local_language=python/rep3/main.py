from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from contextlib import contextmanager
import os

# Initialize FastAPI app
app = FastAPI(title="Book Collection API", version="1.0.0")

# Database setup
DATABASE_PATH = "books.db"

@contextmanager
def get_db():
    """Context manager for database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    try:
        yield conn
    finally:
        conn.close()

# Pydantic models
class BookBase(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

class Book(BookBase):
    id: int

    class Config:
        from_attributes = True

class BookCreate(BookBase):
    pass

class BookUpdate(BookBase):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

# Initialize database
def init_db():
    """Initialize the database with the books table"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
        ''')
        conn.commit()

# Routes
@app.get("/")
async def root():
    return {"message": "Book Collection API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/books", response_model=Book)
async def create_book(book: BookCreate):
    """Create a new book"""
    # Check for required fields manually
    if not book.title:
        raise HTTPException(status_code=400, detail="Title is required")
    if not book.author:
        raise HTTPException(status_code=400, detail="Author is required")
    
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
        ''', (book.title, book.author, book.year, book.isbn))
        conn.commit()
        
        # Get the created book
        book_id = cursor.lastrowid
        book_row = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        
        if book_row:
            # Convert sqlite3.Row to dict for Pydantic model validation
            book_dict = dict(book_row)
            return Book.model_validate(book_dict)
        else:
            raise HTTPException(status_code=500, detail="Failed to create book")

@app.get("/books", response_model=List[Book])
async def read_books(author: Optional[str] = Query(None)):
    """List all books, optionally filtered by author"""
    with get_db() as conn:
        if author:
            rows = conn.execute('SELECT * FROM books WHERE author = ?', (author,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM books').fetchall()
        
        # Convert each sqlite3.Row to dict for Pydantic model validation
        books_list = [dict(row) for row in rows]
        return [Book.model_validate(book_dict) for book_dict in books_list]

@app.get("/books/{book_id}", response_model=Book)
async def read_book(book_id: int):
    """Get a single book by ID"""
    with get_db() as conn:
        book_row = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        
        if book_row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Convert sqlite3.Row to dict for Pydantic model validation
        book_dict = dict(book_row)
        return Book.model_validate(book_dict)

@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book_update: BookUpdate):
    """Update a book"""
    # Check if the book exists
    with get_db() as conn:
        existing_book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        
        if existing_book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Prepare update query
        updates = []
        params = []
        
        if book_update.title is not None:
            updates.append("title = ?")
            params.append(book_update.title)
        if book_update.author is not None:
            updates.append("author = ?")
            params.append(book_update.author)
        if book_update.year is not None:
            updates.append("year = ?")
            params.append(book_update.year)
        if book_update.isbn is not None:
            updates.append("isbn = ?")
            params.append(book_update.isbn)
        
        if not updates:
            raise HTTPException(status_code=400, detail="At least one field must be updated")
        
        # Add ID to params for WHERE clause
        params.append(book_id)
        
        # Execute update
        query = f"UPDATE books SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
        
        # Return updated book
        updated_book_row = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        # Convert sqlite3.Row to dict for Pydantic model validation
        updated_book_dict = dict(updated_book_row)
        return Book.model_validate(updated_book_dict)

@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    """Delete a book"""
    with get_db() as conn:
        # Check if the book exists
        book_row = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        
        if book_row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Delete the book
        conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        
        return {"message": "Book deleted successfully"}

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)