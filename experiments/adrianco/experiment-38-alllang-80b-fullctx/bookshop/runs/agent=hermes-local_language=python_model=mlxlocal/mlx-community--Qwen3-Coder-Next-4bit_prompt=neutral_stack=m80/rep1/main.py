from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from database import get_db_connection, init_db
from models import Book, BookCreate, BookUpdate

app = FastAPI(title="Book API", description="REST API for managing a book collection")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/books")
def list_books(author: Optional[str] = Query(None)):
    """List all books, optionally filtered by author"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if author:
        cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE author = ?", (author,))
    else:
        cursor.execute("SELECT id, title, author, year, isbn FROM books")
    
    rows = cursor.fetchall()
    conn.close()
    
    books = []
    for row in rows:
        books.append(Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4]))
    
    return {"books": books}


@app.get("/books/{book_id}")
def get_book(book_id: int):
    """Get a single book by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return Book(id=row[0], title=row[1], author=row[2], year=row[3], isbn=row[4])


@app.post("/books")
def create_book(book: BookCreate):
    """Create a new book"""
    # Validation
    if not book.title or not book.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if not book.author or not book.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn)
    )
    book_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return Book(id=book_id, title=book.title, author=book.author, year=book.year, isbn=book.isbn)


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookUpdate):
    """Update a book"""
    # Validation
    if book.title is not None and not book.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if book.author is not None and not book.author.strip():
        raise HTTPException(status_code=400, detail="Author cannot be empty")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Build update query
    title = book.title if book.title is not None else row[1]
    author = book.author if book.author is not None else row[2]
    year = book.year if book.year is not None else row[3]
    isbn = book.isbn if book.isbn is not None else row[4]
    
    cursor.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (title, author, year, isbn, book_id)
    )
    conn.commit()
    conn.close()
    
    return Book(id=book_id, title=title, author=author, year=year, isbn=isbn)


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    """Delete a book"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Book deleted successfully", "id": book_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
