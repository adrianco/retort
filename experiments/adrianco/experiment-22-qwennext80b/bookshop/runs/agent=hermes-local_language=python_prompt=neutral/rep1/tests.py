#!/usr/bin/env python3
"""Integration tests for Book Collection API database."""

import pytest
import sqlite3
import os

# Use test database
TEST_DB_PATH = "test_books_api.db"

class TestDatabase:
    @pytest.fixture(scope="class", autouse=True)
    def setup_database(self):
        """Setup test database before tests.""
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
        """)
        conn.commit()
        conn.close()
        
        yield
        
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    
    def test_init_db_creates_table(self, setup_database):
        """Test that database initialization creates the books table."""
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='books'
        """)
        result = cursor.fetchone()
        conn.close()
        assert result is not None, "books table should exist"
    
    def test_create_book(self, setup_database):
        """Test creating a new book."""
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            ("The Great Gatsby", "F. Scott Fitzgerald", 1925, "978-0743273565")
        )
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        assert book_id == 1
        
        conn = sqlite3.connect(TEST_DB_PATH)
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        conn.close()
        
        assert book is not None
        assert book["title"] == "The Great Gatsby"
        assert book["author"] == "F. Scott Fitzgerald"
    
    def test_get_books_empty(self, setup_database):
        """Test getting books when database is empty."""
        conn = sqlite3.connect(TEST_DB_PATH)
        books = conn.execute("SELECT * FROM books").fetchall()
        conn.close()
        
        assert len(books) == 0
    
    def test_get_books_with_data(self, setup_database):
        """Test getting books with data present."""
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute(
            "INSERT INTO books (title, author, year) VALUES (?, ?, ?)",
            ("Book 1", "Author A", 2020)
        )
        conn.commit()
        
        books = conn.execute("SELECT * FROM books").fetchall()
        conn.close()
        
        assert len(books) == 1
        assert books[0]["title"] == "Book 1"
    
    def test_get_books_author_filter(self, setup_database):
        """Test filtering books by author."""
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute("INSERT INTO books (title, author, year) VALUES (?, ?, ?)", ("Book 1", "Author A", 2020))
        conn.execute("INSERT INTO books (title, author, year) VALUES (?, ?, ?)", ("Book 2", "Author B", 2021))
        conn.execute("INSERT INTO books (title, author, year) VALUES (?, ?, ?)", ("Book 3", "Author A", 2022))
        conn.commit()
        
        books = conn.execute("SELECT * FROM books WHERE author LIKE ?", ("%Author A%",)).fetchall()
        conn.close()
        
        assert len(books) == 2
    
    def test_update_book(self, setup_database):
        """Test updating a book."""
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.execute(
            "INSERT INTO books (title, author, year) VALUES (?, ?, ?)",
            ("Original Title", "Original Author", 2020)
        )
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute("UPDATE books SET title = ?, year = ? WHERE id = ?", ("Updated Title", 2021, book_id))
        conn.commit()
        conn.close()
        
        conn = sqlite3.connect(TEST_DB_PATH)
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        conn.close()
        
        assert book["title"] == "Updated Title"
        assert book["year"] == 2021
    
    def test_delete_book(self, setup_database):
        """Test deleting a book."""
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.execute(
            "INSERT INTO books (title, author, year) VALUES (?, ?, ?)",
            ("To Delete", "Delete Author", 2020)
        )
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()
        
        conn = sqlite3.connect(TEST_DB_PATH)
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        conn.close()
        
        assert book is None
