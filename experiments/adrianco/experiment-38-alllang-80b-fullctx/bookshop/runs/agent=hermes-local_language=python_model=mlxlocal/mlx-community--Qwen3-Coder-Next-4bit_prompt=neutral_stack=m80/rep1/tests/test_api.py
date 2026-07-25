import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from database import init_db, get_db_connection


# Use a test database
os.environ["DATABASE_PATH"] = "test_books.db"


@pytest.fixture(scope="module")
def client():
    """Create a test client"""
    init_db()
    # Clean up any existing test data
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books")
    conn.commit()
    conn.close()
    
    yield TestClient(app)
    
    # Clean up test database
    if os.path.exists("test_books.db"):
        os.remove("test_books.db")


def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_create_book(client):
    """Test creating a new book"""
    book_data = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "978-0743273565"
    assert "id" in data
    return data["id"]


def test_create_book_validation_errors(client):
    """Test that creating a book without required fields returns errors"""
    # Missing title
    response = client.post("/books", json={"author": "Test Author"})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    
    # Missing author
    response = client.post("/books", json={"title": "Test Title"})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_list_books(client):
    """Test listing all books"""
    # Create a book first
    book_data = {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "year": 1960
    }
    client.post("/books", json=book_data)
    
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert "books" in data
    assert len(data["books"]) > 0
    assert data["books"][0]["title"] == "To Kill a Mockingbird"


def test_list_books_by_author(client):
    """Test filtering books by author"""
    # Create books with different authors
    client.post("/books", json={
        "title": "Book 1",
        "author": "Author A",
        "year": 2000
    })
    client.post("/books", json={
        "title": "Book 2",
        "author": "Author B",
        "year": 2001
    })
    
    # Filter by author
    response = client.get("/books?author=Author A")
    assert response.status_code == 200
    data = response.json()
    assert len(data["books"]) == 1
    assert data["books"][0]["author"] == "Author A"


def test_get_book_by_id(client):
    """Test getting a single book by ID"""
    # Create a book
    create_response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1949
    })
    book_id = create_response.json()["id"]
    
    # Get the book
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"


def test_get_book_not_found(client):
    """Test getting a non-existent book"""
    response = client.get("/books/99999")
    assert response.status_code == 404


def test_update_book(client):
    """Test updating a book"""
    # Create a book
    create_response = client.post("/books", json={
        "title": "Original Title",
        "author": "Original Author",
        "year": 2000
    })
    book_id = create_response.json()["id"]
    
    # Update the book
    update_data = {
        "title": "Updated Title",
        "year": 2020
    }
    response = client.put(f"/books/{book_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Original Author"  # Unchanged
    assert data["year"] == 2020


def test_update_book_not_found(client):
    """Test updating a non-existent book"""
    update_data = {"title": "New Title"}
    response = client.put("/books/99999", json=update_data)
    assert response.status_code == 404


def test_delete_book(client):
    """Test deleting a book"""
    # Create a book
    create_response = client.post("/books", json={
        "title": "To Delete",
        "author": "Delete Author"
    })
    book_id = create_response.json()["id"]
    
    # Delete the book
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Book deleted successfully"
    
    # Verify the book is gone
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book"""
    response = client.delete("/books/99999")
    assert response.status_code == 404
