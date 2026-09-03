#!/usr/bin/env python3

import sqlite3
import os
import json
import sys

# Add the current directory to path so we can import our main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_setup():
    """Test that database is set up correctly"""
    # Remove any existing database file for a clean test
    if os.path.exists("books.db"):
        os.remove("books.db")
    
    # Import and test database creation
    try:
        from main import init_db
        init_db()
        print("✓ Database initialization works")
        
        # Test database connection
        conn = sqlite3.connect("books.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books';")
        tables = cursor.fetchall()
        conn.close()
        
        if len(tables) > 0:
            print("✓ Database table created successfully")
        else:
            print("✗ Database table not created")
            return False
            
    except Exception as e:
        print(f"✗ Database setup failed: {e}")
        return False
    
    return True

def test_book_operations():
    """Test basic book operations"""
    try:
        from main import Book, BookCreate
        
        # Test Book model
        book = Book(id=1, title="Test Book", author="Test Author", year=2023)
        print("✓ Book model works")
        
        # Test BookCreate model  
        book_create = BookCreate(title="Test Book", author="Test Author")
        print("✓ BookCreate model works")
        
        return True
        
    except Exception as e:
        print(f"✗ Book operations test failed: {e}")
        return False

def test_main_logic():
    """Test that main logic files are syntactically correct"""
    try:
        # Just check if we can import the main module without syntax errors
        import main
        print("✓ Main module imports successfully")
        return True
    except Exception as e:
        print(f"✗ Main module import failed: {e}")
        return False

if __name__ == "__main__":
    print("Running basic implementation checks...")
    print()
    
    success = True
    success &= test_database_setup()
    print()
    success &= test_book_operations()
    print()
    success &= test_main_logic()
    print()
    
    if success:
        print("✓ All basic checks passed!")
        sys.exit(0)
    else:
        print("✗ Some checks failed!")
        sys.exit(1)