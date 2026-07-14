import pytest
from fastapi.testclient import TestClient
from main import app
import sqlite3
import os

# Create a test client for the app
client = TestClient(app)

# Helper function to clean up test database
def cleanup_db():
    """Clean up the test database"""
    if os.path.exists("books.db"):
        os.remove("books.db")

# Setup and teardown for tests
@pytest.fixture(scope="function")
def setup_and_teardown():
    """Setup and teardown for each test"""
    # Clean up before test
    cleanup_db()
    # Initialize database
    from main import init_db
    init_db()
    yield
    # Clean up after test
    cleanup_db()

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book(setup_and_teardown):
    """Test creating a book"""
    # Test with valid data
    response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1948
    assert data["isbn"] == "978-0-452-28423-4"
    assert "id" in data

def test_create_book_missing_fields(setup_and_teardown):
    """Test creating a book with missing required fields"""
    # Test with missing title
    response = client.post("/books", json={
        "author": "George Orwell"
    })
    assert response.status_code == 400

    # Test with missing author
    response = client.post("/books", json={
        "title": "1984"
    })
    assert response.status_code == 400

def test_get_all_books(setup_and_teardown):
    """Test getting all books"""
    # First create some books
    client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    
    client.post("/books", json={
        "title": "Animal Farm",
        "author": "George Orwell",
        "year": 1945
    })
    
    # Get all books
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_get_books_by_author(setup_and_teardown):
    """Test getting books filtered by author"""
    # First create some books
    client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    
    client.post("/books", json={
        "title": "Animal Farm",
        "author": "George Orwell",
        "year": 1945
    })
    
    client.post("/books", json={
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "year": 1960
    })
    
    # Get books by George Orwell
    response = client.get("/books?author=George%20Orwell")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Verify all books are by George Orwell
    for book in data:
        assert book["author"] == "George Orwell"

def test_get_single_book(setup_and_teardown):
    """Test getting a single book by ID"""
    # Create a book first
    create_response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    
    book_id = create_response.json()["id"]
    
    # Get the book by ID
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1948

def test_get_nonexistent_book(setup_and_teardown):
    """Test getting a book that doesn't exist"""
    response = client.get("/books/999")
    assert response.status_code == 404

def test_update_book(setup_and_teardown):
    """Test updating a book"""
    # Create a book first
    create_response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    
    book_id = create_response.json()["id"]
    
    # Update the book
    response = client.put(f"/books/{book_id}", json={
        "title": "Nineteen Eighty-Four",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Nineteen Eighty-Four"
    assert data["isbn"] == "978-0-452-28423-4"

def test_update_nonexistent_book(setup_and_teardown):
    """Test updating a book that doesn't exist"""
    response = client.put("/books/999", json={
        "title": "1984",
        "author": "George Orwell"
    })
    assert response.status_code == 404

def test_update_book_missing_fields(setup_and_teardown):
    """Test updating a book with no fields to update"""
    # Create a book first
    create_response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    
    book_id = create_response.json()["id"]
    
    # Try to update with no fields
    response = client.put(f"/books/{book_id}", json={})
    assert response.status_code == 400

def test_delete_book(setup_and_teardown):
    """Test deleting a book"""
    # Create a book first
    create_response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    
    book_id = create_response.json()["id"]
    
    # Delete the book
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Book deleted successfully"}

def test_delete_nonexistent_book(setup_and_teardown):
    """Test deleting a book that doesn't exist"""
    response = client.delete("/books/999")
    assert response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"])