import pytest
import sqlite3
from fastapi.testclient import TestClient
from main import app, Book, init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Initialize database before each test
    init_db()
    # Clean up any existing data
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books")
    conn.commit()
    conn.close()
    yield

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948,
        "isbn": "978-0-452-28423-4"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1948
    assert data["isbn"] == "978-0-452-28423-4"
    assert "id" in data

def test_create_book_missing_required_fields():
    response = client.post("/books", json={
        "title": "1984"
        # Missing author
    })
    assert response.status_code == 422
    # Check that the error contains information about missing required field
    error_detail = response.json()
    assert 'detail' in error_detail
    assert len(error_detail['detail']) > 0
    assert 'author' in str(error_detail['detail'][0])

def test_read_books():
    # First create a book
    client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    
    # Then get all books
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "1984"
    assert data[0]["author"] == "George Orwell"

def test_read_books_with_filter():
    # Create two books
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
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965
    })
    
    # Get books by author
    response = client.get("/books?author=George Orwell")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(book["author"] == "George Orwell" for book in data)

def test_read_single_book():
    # Create a book
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

def test_read_nonexistent_book():
    response = client.get("/books/999")
    assert response.status_code == 404

def test_update_book():
    # Create a book
    create_response = client.post("/books", json={
        "title": "1984",
        "author": "George Orwell",
        "year": 1948
    })
    book_id = create_response.json()["id"]
    
    # Update the book
    response = client.put(f"/books/{book_id}", json={
        "title": "Nineteen Eighty-Four",
        "year": 1949
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Nineteen Eighty-Four"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1949

def test_update_nonexistent_book():
    response = client.put("/books/999", json={
        "title": "Nineteen Eighty-Four"
    })
    assert response.status_code == 404

def test_delete_book():
    # Create a book
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
    
    # Verify the book is deleted
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404

def test_delete_nonexistent_book():
    response = client.delete("/books/999")
    assert response.status_code == 404