"""
Additional unit tests to ensure core functionality
"""
import pytest
import os
import sqlite3
from fastapi.testclient import TestClient
from app import app, init_db

# Create a clean database for testing
def setup_database():
    if os.path.exists("books.db"):
        os.remove("books.db")
    init_db()

client = TestClient(app)

def test_duplicate_isbn_rejection():
    """Test that duplicate ISBNs are rejected"""
    setup_database()
    
    # Create first book
    book1 = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}
    client.post("/books", json=book1)
    
    # Try to create another book with same ISBN
    book2 = {"title": "Another Book", "author": "Another Author", "year": 1949, "isbn": "978-0-452-28423-4"}
    response = client.post("/books", json=book2)
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_empty_database_returns_empty_list():
    """Test that empty database returns empty list"""
    setup_database()
    
    response = client.get("/books")
    assert response.status_code == 200
    assert response.json() == []

def test_book_validation_errors():
    """Test validation of required fields"""
    setup_database()
    
    # Test missing title
    response = client.post("/books", json={
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    })
    assert response.status_code == 422
    
    # Test missing author
    response = client.post("/books", json={
        "title": "1984",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    })
    assert response.status_code == 422
    
    # Test missing year
    response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "isbn": "978-0-452-28423-4"
    })
    assert response.status_code == 422
    
    # Test missing isbn
    response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__, "-v"])