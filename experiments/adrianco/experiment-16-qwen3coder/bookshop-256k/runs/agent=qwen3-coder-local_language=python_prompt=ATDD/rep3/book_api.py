#!/usr/bin/env python3
"""
Core Book API implementation - ATDD compliant
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any

# Database setup
DATABASE = "books.db"

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create books table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
    ''')
    
    conn.commit()
    conn.close()

class BookAPI:
    def __init__(self):
        self.db_file = DATABASE
        init_db()
    
    def create_book(self, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new book"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO books (title, author, year, isbn)
                VALUES (?, ?, ?, ?)
            ''', (
                book_data["title"],
                book_data["author"],
                book_data.get("year"),
                book_data.get("isbn")
            ))
            
            book_id = cursor.lastrowid
            conn.commit()
            
            # Return created book
            cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
            row = cursor.fetchone()
            
            return {
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "year": row[3],
                "isbn": row[4]
            }
            
        except sqlite3.IntegrityError:
            raise ValueError("ISBN already exists")
        finally:
            conn.close()
    
    def list_books(self, author: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all books, optionally filtered by author"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if author:
            cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
        else:
            cursor.execute('SELECT * FROM books')
        
        rows = cursor.fetchall()
        conn.close()
        
        books = []
        for row in rows:
            books.append({
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "year": row[3],
                "isbn": row[4]
            })
        
        return books
    
    def get_book(self, book_id: int) -> Dict[str, Any]:
        """Get a single book by ID"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            raise ValueError("Book not found")
        
        return {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "year": row[3],
            "isbn": row[4]
        }
    
    def update_book(self, book_id: int, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a book"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if book exists
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        existing_book = cursor.fetchone()
        
        if not existing_book:
            raise ValueError("Book not found")
        
        # Build update query
        updates = []
        values = []
        
        if "title" in book_data:
            updates.append("title = ?")
            values.append(book_data["title"])
        if "author" in book_data:
            updates.append("author = ?")
            values.append(book_data["author"])
        if "year" in book_data:
            updates.append("year = ?")
            values.append(book_data["year"])
        if "isbn" in book_data:
            updates.append("isbn = ?")
            values.append(book_data["isbn"])
        
        if not updates:
            raise ValueError("No fields to update")
        
        # Add book_id to values for WHERE clause
        values.append(book_id)
        
        # Execute update
        query = f"UPDATE books SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        
        if cursor.rowcount == 0:
            raise ValueError("Book not found")
        
        conn.commit()
        
        # Return updated book
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        row = cursor.fetchone()
        conn.close()
        
        return {
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "year": row[3],
            "isbn": row[4]
        }
    
    def delete_book(self, book_id: int) -> Dict[str, str]:
        """Delete a book"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        
        if cursor.rowcount == 0:
            raise ValueError("Book not found")
        
        conn.commit()
        conn.close()
        
        return {"message": "Book deleted successfully"}

if __name__ == "__main__":
    # Simple test of core functionality
    api = BookAPI()
    
    # Test 1: Create a book
    book_data = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0-7432-7356-5"
    }
    
    print("Creating book...")
    created_book = api.create_book(book_data)
    print(f"✓ Created: {created_book['title']} (ID: {created_book['id']})")
    
    # Test 2: List books
    print("Listing books...")
    books = api.list_books()
    print(f"✓ Found {len(books)} book(s)")
    
    # Test 3: Get book by ID
    print("Getting book by ID...")
    book = api.get_book(created_book['id'])
    print(f"✓ Retrieved: {book['title']}")
    
    # Test 4: Update book
    print("Updating book...")
    updated_book = api.update_book(created_book['id'], {"title": "The Great Gatsby - Updated"})
    print(f"✓ Updated title to: {updated_book['title']}")
    
    # Test 5: Delete book
    print("Deleting book...")
    result = api.delete_book(created_book['id'])
    print(f"✓ Deleted: {result['message']}")
    
    print("\n🎉 All unit tests passed!")