#!/usr/bin/env python3
"""
Test script to verify the API functionality without running the server continuously.
"""

import sqlite3
import json
from main import app, init_db
from fastapi.testclient import TestClient

# Initialize the database
init_db()

# Create test client
client = TestClient(app)

def test_all_endpoints():
    print("Testing Book Collection API endpoints...")
    
    # Test health check
    print("1. Testing health check...")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    print("   ✓ Health check passed")
    
    # Test creating a book
    print("2. Testing book creation...")
    book_data = {
        "title": "1984",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    created_book = response.json()
    assert created_book["title"] == "1984"
    assert created_book["author"] == "George Orwell"
    assert created_book["year"] == 1948
    assert created_book["isbn"] == "978-0-452-28423-4"
    print("   ✓ Book creation passed")
    
    # Test listing books
    print("3. Testing list books...")
    response = client.get("/books")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["title"] == "1984"
    print("   ✓ List books passed")
    
    # Test getting a specific book
    print("4. Testing get specific book...")
    book_id = created_book["id"]
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    retrieved_book = response.json()
    assert retrieved_book["title"] == "1984"
    assert retrieved_book["author"] == "George Orwell"
    print("   ✓ Get specific book passed")
    
    # Test updating a book
    print("5. Testing book update...")
    response = client.put(f"/books/{book_id}", json={
        "title": "Nineteen Eighty-Four",
        "year": 1949
    })
    assert response.status_code == 200
    updated_book = response.json()
    assert updated_book["title"] == "Nineteen Eighty-Four"
    assert updated_book["year"] == 1949
    print("   ✓ Book update passed")
    
    # Test deleting a book
    print("6. Testing book deletion...")
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Book deleted successfully"}
    print("   ✓ Book deletion passed")
    
    # Test that deleted book is gone
    print("7. Testing that deleted book is gone...")
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404
    print("   ✓ Deleted book verification passed")
    
    print("\nAll tests passed! ✓")

if __name__ == "__main__":
    test_all_endpoints()