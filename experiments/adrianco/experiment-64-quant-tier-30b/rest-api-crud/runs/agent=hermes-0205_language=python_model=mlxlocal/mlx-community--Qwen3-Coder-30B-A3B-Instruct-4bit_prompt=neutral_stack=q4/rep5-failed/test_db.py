#!/usr/bin/env python3
# Simple test to verify basic functionality
import sqlite3
import os

# Test database creation and basic operations
def test_database():
    # Create test database
    conn = sqlite3.connect('test_books.db')
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
    """)
    
    # Insert test data
    cursor.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
                   ("Test Book", "Test Author", 2023, "1234567890"))
    
    conn.commit()
    
    # Query data
    cursor.execute("SELECT * FROM books")
    results = cursor.fetchall()
    
    print(f"Database test successful. Found {len(results)} books")
    conn.close()
    
    # Clean up
    os.remove('test_books.db')
    print("Database test cleaned up")

if __name__ == "__main__":
    test_database()