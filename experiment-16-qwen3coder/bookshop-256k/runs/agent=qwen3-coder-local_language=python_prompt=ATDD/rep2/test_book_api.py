import pytest
import json
import os
import sqlite3
from fastapi.testclient import TestClient
from app import app, init_db

# Initialize a fresh database before each test
def setup_database():
    # Remove existing database file
    if os.path.exists("books.db"):
        os.remove("books.db")
    
    # Initialize fresh database
    init_db()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test - ensures clean database"""
    setup_database()
    yield
    # Cleanup after test if needed (database is cleaned per test)

def test_health_check():
    """Test that the health check endpoint works"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    """Test creating a new book"""
    book_data = {
        "title": "1984",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == book_data["title"]
    assert data["author"] == book_data["author"]
    assert data["year"] == book_data["year"]
    assert data["isbn"] == book_data["isbn"]
    assert "id" in data

def test_create_book_missing_title():
    """Test that creating a book without title fails"""
    book_data = {
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    
    response = client.post("/books", json=book_data)
    assert response.status_code == 422

def test_create_book_missing_author():
    """Test that creating a book without author fails"""
    book_data = {
        "title": "1984",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    
    response = client.post("/books", json=book_data)
    assert response.status_code == 422

def test_get_all_books():
    """Test listing all books"""
    # First create some books
    book1 = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}
    book2 = {"title": "Animal Farm", "author": "George Orwell", "year": 1945, "isbn": "978-0-452-28424-1"}
    
    client.post("/books", json=book1)
    client.post("/books", json=book2)
    
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Check that we have both books
    book_titles = [book["title"] for book in data]
    assert "1984" in book_titles
    assert "Animal Farm" in book_titles

def test_get_all_books_filtered_by_author():
    """Test listing books filtered by author"""
    # First create some books
    book1 = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}
    book2 = {"title": "Animal Farm", "author": "George Orwell", "year": 1945, "isbn": "978-0-452-28424-1"}
    book3 = {"title": "To Kill a Mockingbird", "author": "Harper Lee", "year": 1960, "isbn": "978-0-06-112008-4"}
    
    client.post("/books", json=book1)
    client.post("/books", json=book2)
    client.post("/books", json=book3)
    
    # Test filtering by George Orwell
    response = client.get("/books?author=George%20Orwell")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for book in data:
        assert book["author"] == "George Orwell"
    
    # Test filtering by Harper Lee
    response = client.get("/books?author=Harper%20Lee")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "Harper Lee"

def test_get_book_by_id():
    """Test getting a single book by ID"""
    book_data = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}
    
    # Create a book first
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    # Get the book by ID
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == book_data["title"]
    assert data["author"] == book_data["author"]
    assert data["year"] == book_data["year"]
    assert data["isbn"] == book_data["isbn"]
    assert data["id"] == book_id

def test_get_nonexistent_book():
    """Test getting a book that doesn't exist"""
    response = client.get("/books/999")
    assert response.status_code == 404

def test_update_book():
    """Test updating a book"""
    book_data = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}
    
    # Create a book first
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    # Update the book
    updated_data = {
        "title": "Nineteen Eighty-Four",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    }
    
    response = client.put(f"/books/{book_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == updated_data["title"]
    assert data["author"] == updated_data["author"]
    assert data["year"] == updated_data["year"]
    assert data["isbn"] == updated_data["isbn"]
    assert data["id"] == book_id

def test_update_nonexistent_book():
    """Test updating a book that doesn't exist"""
    updated_data = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}
    
    response = client.put("/books/999", json=updated_data)
    assert response.status_code == 404

def test_delete_book():
    """Test deleting a book"""
    book_data = {"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}
    
    # Create a book first
    create_response = client.post("/books", json=book_data)
    book_id = create_response.json()["id"]
    
    # Delete the book
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    
    # Verify it's deleted
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404

def test_delete_nonexistent_book():
    """Test deleting a book that doesn't exist"""
    response = client.delete("/books/999")
    assert response.status_code == 404