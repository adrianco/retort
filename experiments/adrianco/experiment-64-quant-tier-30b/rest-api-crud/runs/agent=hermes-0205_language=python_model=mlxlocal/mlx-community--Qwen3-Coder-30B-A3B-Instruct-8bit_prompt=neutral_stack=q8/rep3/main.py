from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

app = FastAPI(title="Book Collection API")

# Database setup
DB_NAME = "books.db"

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

def init_db():
    """Initialize the database with the books table"""
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

@app.on_event("startup")
def startup_event():
    """Initialize database when the app starts"""
    init_db()

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/books", response_model=Book)
def create_book(book: BookCreate):
    """Create a new book"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
    ''', (book.title, book.author, book.year, book.isbn))
    
    book_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Return the created book
    return Book(id=book_id, **book.dict())

@app.get("/books", response_model=List[Book])
def get_books(author: Optional[str] = Query(None)):
    """List all books, optionally filtered by author"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if author:
        cursor.execute('''
            SELECT id, title, author, year, isbn
            FROM books
            WHERE author LIKE ?
            ORDER BY title
        ''', (f'%{author}%',))
    else:
        cursor.execute('''
            SELECT id, title, author, year, isbn
            FROM books
            ORDER BY title
        ''')
    
    books = []
    for row in cursor.fetchall():
        books.append(Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4]))
    
    conn.close()
    return books

@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    """Get a single book by ID"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, author, year, isbn
        FROM books
        WHERE id = ?
    ''', (book_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])

@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate):
    """Update a book"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT id FROM books WHERE id = ?', (book_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Prepare update query
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
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(book_id)
    query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
    
    cursor.execute(query, values)
    conn.commit()
    
    # Fetch the updated book
    cursor.execute('''
        SELECT id, title, author, year, isbn
        FROM books
        WHERE id = ?
    ''', (book_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])

@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    """Delete a book"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT id FROM books WHERE id = ?', (book_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Book deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)