import sqlite3
import os

def test_database_creation():
    """Test that database is created properly"""
    # Check if database file exists and can be accessed
    db_path = "books.db"
    assert os.path.exists(db_path), "Database file should exist after initialization"
    
    # Test database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("PRAGMA table_info(books)")
    columns = cursor.fetchall()
    assert len(columns) > 0, "Books table should have columns"
    
    conn.close()

def test_book_creation():
    """Test creating a book in database"""
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    
    # Insert test book
    cursor.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
                   ("Test Book", "Test Author", 2023, "1234567890"))
    
    conn.commit()
    conn.close()
    
    # Verify book was inserted
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE title = ?", ("Test Book,))
    result = cursor.fetchone()
    
    assert result is not None, "Book should exist in database"
    assert result[1] == "Test Book", "Book title should match"
    assert result[2] == "Test Author", "Book author should match"
    
    conn.close()

def test_database_schema():
    """Test that database has correct schema"""
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    
    # Check table structure
    cursor.execute("PRAGMA table_info(books)")
    columns = cursor.fetchall()
    
    # Should have at least 5 columns (id, title, author, year, isbn)
    assert len(columns) >= 5, "Database should have at least 5 columns"
    
    conn.close()