#!/usr/bin/env python3
import sqlite3
import os

# Simple test that demonstrates basic functionality
def test_database():
    """Test basic database operations"""
    # Setup database
    DATABASE = "test_books.db"
    
    # Create table
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
    
    # Test data
    test_data = [
        ("Book 1", "Author 1", 2023, "1234567890"),
        ("Book 2", "Author 2", 2024, "0987654321")
    ]
    
    # Insert test data
    for data in test_data:
        cursor.execute("INSERT OR IGNORE INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", data)
    
    conn.commit()
    
    # Test queries
    cursor.execute("SELECT * FROM books")
    all_books = cursor.fetchall()
    
    print(f"Found {len(all_books)} books in database")
    for book in all_books:
        print(f"Book: {book}")
    
    conn.close()
    
    # Clean up
    os.remove(DATABASE)
    print("Database test completed successfully")

if __name__ == "__main__":
    test_database()