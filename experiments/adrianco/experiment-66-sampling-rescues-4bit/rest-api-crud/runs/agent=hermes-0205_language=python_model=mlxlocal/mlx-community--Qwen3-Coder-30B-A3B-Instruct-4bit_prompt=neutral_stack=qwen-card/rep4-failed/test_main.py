import pytest
import sqlite3
import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def setup_db():
    """Setup test database"""
    conn = sqlite3.connect("test.db")
    cursor = conn.cursor()
    
    # Create books table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
    """)
    
    conn.commit()
    conn.close()

def teardown_db():
    """Clean up test database"""
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture(scope="function")
def test_client():
    """Setup test client"""
    setup_db()
    yield client
    teardown_db()

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    """Test creating a book"""
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2020,
        "isbn": "1234567890"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"
    assert data["year"] == 2020
    assert data["isbn"] == "1234567890"

def test_get_book_by_id():
    """Test getting a book by ID"""
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2020,
        "isbn": "1234567890"
    })
    book_id = response.json()["id"]
    
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"
    assert data["year"] == 2020
    assert data["isbn"] == "1234567890"

def test_update_book():
    """Test updating a book"""
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2020,
        "isbn": "1234567890"
    })
    book_id = response.json()["id"]
    
    response = client.put(f"/books/{book_id}", json={
        "title": "Updated Test Book",
        "author": "Updated Author",
        "year": 2021,
        "isbn": "1234567890"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Test Book"
    assert data["author"] == "Updated Author"
    assert data["year"] == 2021
    assert data["isbn"] == "1234567890"

def test_delete_book():
    """Test deleting a book"""
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2020,
        "isbn": "1234567890"
    })
    book_id = response.json()["id"]
    
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Book deleted successfully"}

def test_get_nonexistent_book():
    """Test getting a non-existent book"""
    response = client.get("/books/99999")
    assert response.status_code == 404