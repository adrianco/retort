#!/usr/bin/env python3
import sqlite3
from typing import Optional, List, Dict, Any

# Database setup
DATABASE = "books.db"

def init_db():
    """Initialize the database with the books table"""
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

def create_book(title: str, author: str, year: Optional[int] = None, isbn: Optional[str] = None) -> int:
    """Create a new book"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
        conn.close()
        return book_id
    except sqlite3.IntegrityError:
        conn.close()
        raise Exception("Book with this ISBN already exists")

def get_all_books(author: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all books, optionally filtered by author"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if author:
        cursor.execute("SELECT * FROM books WHERE author=?", (author,))
    else:
        cursor.execute("SELECT * FROM books")
    
    columns = [description[0] for description in cursor.description]
    books = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return books

def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    """Get a book by ID"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id=?", (book_id,))
    book = cursor.fetchone()
    conn.close()
    
    if book:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, book))
    return None

def update_book(book_id: int, title: Optional[str] = None, author: Optional[str] = None, year: Optional[int] = None, isbn: Optional[str] = None) -> bool:
    """Update a book by ID"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT id FROM books WHERE id=?", (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        conn.close()
        return False
    
    # Build dynamic update query
    update_fields = []
    params = []
    
    if title is not None:
        update_fields.append("title=?")
        params.append(title)
    if author is not None:
        update_fields.append("author=?")
        params.append(author)
    if year is not None:
        update_fields.append("year=?")
        params.append(year)
    if isbn is not None:
        update_fields.append("isbn=?")
        params.append(isbn)
    
    if not update_fields:
        conn.close()
        return True
    
    # Prepare and execute update
    query = f"UPDATE books SET {', '.join(update_fields)} WHERE id=?"
    params.append(book_id)
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    
    return True

def delete_book(book_id: int) -> bool:
    """Delete a book by ID"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT id FROM books WHERE id=?", (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        conn.close()
        return False
    
    cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    
    return True

def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}

def main():
    """Main function to demonstrate functionality"""
    print("Book API implementation")
    print("This demonstrates the required functionality")
    
    # Initialize database
    init_db()
    
    try:
        # Create test books
        book1_id = create_book("Test Book 1", "Test Author 1", 2023, "1234567890")
        print(f"Created book with ID: {book1_id}")
        
        book2_id = create_book("Test Book 2", "Test Author 2", 2024, "0987654321")
        print(f"Created book with ID: {book2_id}")
        
        # Get all books
        all_books = get_all_books()
        print(f"Found {len(all_books)} books")
        
        # Get specific book by ID
        book = get_book_by_id(book1_id)
        print(f"Book details: {book}")
        
        # Update book
        update_book(book1_id, title="Updated Test Book", year=2025)
        updated_book = get_book_by_id(book1_id)
        print(f"Updated book details: {updated_book}")
        
        # Get all books with author filter
        author_books = get_all_books(author="Test Author 1")
        print(f"Found {len(author_books)} books by author")
        
        # Delete a book
        delete_book(book2_id)
        print("Deleted book with ID: " + str(book2_id))
        
        print("Database operations completed successfully")
        
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()