from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

# Initialize FastAPI app
app = FastAPI(title="Book Collection API", version="1.0.0")

# Database setup
DB_NAME = "books.db"

class Book(BaseModel):
    id: Optional[int] = None
    title: str
    author: str
    year: int
    isbn: str

class BookCreate(BaseModel):
    title: str
    author: str
    year: int
    isbn: str

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

def init_db():
    """Initialize the database with the books table"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER NOT NULL,
            isbn TEXT NOT NULL UNIQUE
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to the Book Collection API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/books", response_model=Book, status_code=201)
async def create_book(book: BookCreate):
    """Create a new book"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
        ''', (book.title, book.author, book.year, book.isbn))
        
        conn.commit()
        book_id = cursor.lastrowid
        
        # Retrieve the created book
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        row = cursor.fetchone()
        
        if row:
            return Book(
                id=row[0],
                title=row[1],
                author=row[2],
                year=row[3],
                isbn=row[4]
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create book")
            
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="Book with this ISBN already exists")
        else:
            raise HTTPException(status_code=400, detail="Database error")
    finally:
        conn.close()

@app.get("/books", response_model=List[Book])
async def get_books(author: Optional[str] = None):
    """Get all books, optionally filtered by author"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        Book(
            id=row[0],
            title=row[1],
            author=row[2],
            year=row[3],
            isbn=row[4]
        ) for row in rows
    ]

@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int):
    """Get a single book by ID"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return Book(
        id=row[0],
        title=row[1],
        author=row[2],
        year=row[3],
        isbn=row[4]
    )

@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book: BookUpdate):
    """Update a book"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Build the update query dynamically
    update_fields = []
    values = []
    
    if book.title is not None:
        update_fields.append("title = ?")
        values.append(book.title)
    if book.author is not None:
        update_fields.append("author = ?")
        values.append(book.author)
    if book.year is not None:
        update_fields.append("year = ?")
        values.append(book.year)
    if book.isbn is not None:
        update_fields.append("isbn = ?")
        values.append(book.isbn)
    
    if not update_fields:
        # No fields to update, return the existing book
        conn.close()
        return Book(
            id=existing_book[0],
            title=existing_book[1],
            author=existing_book[2],
            year=existing_book[3],
            isbn=existing_book[4]
        )
    
    # Add the ID to the values for WHERE clause
    values.append(book_id)
    
    # Execute the update
    query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, values)
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    
    conn.commit()
    
    # Retrieve the updated book
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to update book")
    
    return Book(
        id=row[0],
        title=row[1],
        author=row[2],
        year=row[3],
        isbn=row[4]
    )

@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    """Delete a book"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Book deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)