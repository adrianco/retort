from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

app = FastAPI(title="Book API", description="REST API for managing a book collection")

# Database setup
DATABASE = "books.db"

def init_db():
    """Initialize the database with the books table"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create books table if it doesn't exist
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

# Data models
class BookBase(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

class Book(BookBase):
    id: int

class BookCreate(BookBase):
    pass

class BookUpdate(BookBase):
    pass

# Initialize database
init_db()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/books", response_model=List[Book])
async def get_books(author: Optional[str] = None):
    """Get all books, optionally filtered by author"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if author:
        cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE author = ?", (author,))
    else:
        cursor.execute("SELECT id, title, author, year, isbn FROM books")
    
    rows = cursor.fetchall()
    conn.close()
    
    books = []
    for row in rows:
        book = Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])
        books.append(book)
    
    return books

@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int):
    """Get a single book by ID"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])
    conn.close()
    
    return book

@app.post("/books", response_model=Book)
async def create_book(book: BookCreate):
    """Create a new book"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.year, book.isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
        conn.close()
        
        # Return the created book with its ID
        return Book(id=book_id, title=book.title, author=book.author, year=book.year, isbn=book.isbn)
    
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail="ISBN already exists")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail="Error creating book")

@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book: BookUpdate):
    """Update a book by ID"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        cursor.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (book.title, book.author, book.year, book.isbn, book_id)
        )
        conn.commit()
        
        # Return updated book
        cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE id=?", (book_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            updated_book = Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])
            return updated_book
        else:
            raise HTTPException(status_code=404, detail="Book not found")
    
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail="ISBN already exists")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail="Error updating book")

@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    """Delete a book by ID"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Book deleted successfully"}

# Test the database connection and setup
@app.get("/test")
async def test():
    """Test endpoint"""
    return {"message": "Database connection working"}