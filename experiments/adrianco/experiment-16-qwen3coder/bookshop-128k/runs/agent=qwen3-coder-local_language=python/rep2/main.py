from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

# Initialize FastAPI app
app = FastAPI(title="Book Collection API", description="REST API for managing a book collection")

# Database setup
DB_NAME = "books.db"

# Pydantic models
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
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Helper function to get a book by ID
def get_book_by_id(book_id: int) -> Optional[Book]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])
    return None

# Helper function to get all books with optional filtering
def get_books(author: Optional[str] = None) -> List[Book]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if author:
        cursor.execute("SELECT * FROM books WHERE author LIKE ?", (f"%{author}%",))
    else:
        cursor.execute("SELECT * FROM books")
    
    rows = cursor.fetchall()
    conn.close()
    
    return [Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4]) for row in rows]

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Create a new book
@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate):
    # Validate required fields
    if not book.title or not book.author:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title and author are required"
        )
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn)
    )
    book_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Return the created book
    created_book = get_book_by_id(book_id)
    return created_book

# Get all books (with optional author filter)
@app.get("/books", response_model=List[Book])
async def read_books(author: Optional[str] = None):
    return get_books(author=author)

# Get a single book by ID
@app.get("/books/{book_id}", response_model=Book)
async def read_book(book_id: int):
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return book

# Update a book
@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book_update: BookUpdate):
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Prepare update data
    update_fields = []
    update_values = []
    
    if book_update.title is not None:
        update_fields.append("title = ?")
        update_values.append(book_update.title)
    
    if book_update.author is not None:
        update_fields.append("author = ?")
        update_values.append(book_update.author)
    
    if book_update.year is not None:
        update_fields.append("year = ?")
        update_values.append(book_update.year)
    
    if book_update.isbn is not None:
        update_fields.append("isbn = ?")
        update_values.append(book_update.isbn)
    
    # If no fields to update, return the book as is
    if not update_fields:
        return book
    
    # Add book_id to update values
    update_values.append(book_id)
    
    # Build and execute update query
    query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, update_values)
    conn.commit()
    conn.close()
    
    # Return the updated book
    updated_book = get_book_by_id(book_id)
    return updated_book

# Delete a book
@app.delete("/books/{book_id}", response_model=dict)
async def delete_book(book_id: int):
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Book deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)