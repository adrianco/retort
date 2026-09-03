import pytest
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    """Test creating a new book"""
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"
    assert data["year"] == 2023
    assert data["isbn"] == "1234567890"
    assert "id" in data

def test_get_books():
    """Test getting all books"""
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_book_by_id():
    """Test getting a book by ID"""
    # First create a book to get its ID
    create_response = client.post("/books", json={
        "title": "Test Book 2",
        "author": "Test Author 2",
        "year": 2022
    })
    assert create_response.status_code == 200
    book_id = create_response.json()["id"]
    
    # Now get the book by ID
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book 2"
    assert data["author"] == "Test Author 2"
    assert data["year"] == 2022

def test_get_nonexistent_book():
    """Test getting a book that doesn't exist"""
    response = client.get("/books/99999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}

def test_update_book():
    """Test updating a book"""
    # First create a book
    create_response = client.post("/books", json={
        "title": "Original Title",
        "author": "Original Author",
        "year": 2020
    })
    assert create_response.status_code == 200
    book_id = create_response.json()["id"]
    
    # Now update the book
    response = client.put(f"/books/{book_id}", json={
        "title": "Updated Title",
        "author": "Updated Author"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Updated Author"
    assert data["year"] == 2020  # Unchanged

def test_update_nonexistent_book():
    """Test updating a book that doesn't exist"""
    response = client.put("/books/99999", json={
        "title": "Updated Title"
    })
    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}

def test_delete_book():
    """Test deleting a book"""
    # First create a book
    create_response = client.post("/books", json={
        "title": "Book to Delete",
        "author": "Author to Delete"
    })
    assert create_response.status_code == 200
    book_id = create_response.json()["id"]
    
    # Now delete the book
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Book deleted successfully"}

def test_delete_nonexistent_book():
    """Test deleting a book that doesn't exist"""
    response = client.delete("/books/99999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}

def test_filter_books_by_author():
    """Test filtering books by author"""
    response = client.get("/books", params={"author": "Test"})
    assert response.status_code == 200
    data = response.json()
    # Should return books with "Test" in author name
    assert isinstance(data, list)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])