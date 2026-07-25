"""Integration tests for the Book API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db, init_db
from database import Base, Book

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override get_db dependency to use test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create a test client with fresh database for each test."""
    # Create tables before each test
    Base.metadata.create_all(bind=engine)
    
    test_client = TestClient(app)
    yield test_client
    
    # Drop tables after each test
    Base.metadata.drop_all(bind=engine)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] in ["connected", "test-mode"]


def test_create_book(client):
    """Test creating a new book."""
    book_data = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565"
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["id"] == 1


def test_create_book_missing_title(client):
    """Test creating a book without title."""
    book_data = {
        "author": "Some Author",
        "year": 2024
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 422


def test_create_book_missing_author(client):
    """Test creating a book without author."""
    book_data = {
        "title": "Some Book",
        "year": 2024
    }
    response = client.post("/books", json=book_data)
    assert response.status_code == 422


def test_list_books_empty(client):
    """Test listing books when database is empty."""
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_books_with_data(client):
    """Test listing books with data in database."""
    # Add some test data using the test client
    book1 = {"title": "Book One", "author": "Author A", "year": 2020, "isbn": "111-1111111111"}
    book2 = {"title": "Book Two", "author": "Author B", "year": 2021, "isbn": "222-2222222222"}
    
    client.post("/books", json=book1)
    client.post("/books", json=book2)

    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_books_filter_by_author(client):
    """Test filtering books by author."""
    # Add some test data
    books_data = [
        {"title": "Book One", "author": "George Orwell", "year": 1949, "isbn": "111-1111111111"},
        {"title": "Book Two", "author": "George Orwell", "year": 1984, "isbn": "222-2222222222"},
        {"title": "Book Three", "author": "Other Author", "year": 2020, "isbn": "333-3333333333"},
    ]
    
    for book_data in books_data:
        client.post("/books", json=book_data)

    response = client.get("/books?author=George%20Orwell")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(book["author"] == "George Orwell" for book in data)


def test_get_book_not_found(client):
    """Test getting a non-existent book."""
    response = client.get("/books/999")
    assert response.status_code == 404


def test_get_book_found(client):
    """Test getting an existing book."""
    book_data = {"title": "Test Book", "author": "Test Author", "year": 2024, "isbn": "123-1234567890"}
    response = client.post("/books", json=book_data)
    assert response.status_code == 201

    response = client.get("/books/1")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"


def test_update_book_not_found(client):
    """Test updating a non-existent book."""
    book_data = {"title": "Updated Title"}
    response = client.put("/books/999", json=book_data)
    assert response.status_code == 404


def test_update_book(client):
    """Test updating an existing book."""
    book_data = {"title": "Original Title", "author": "Original Author", "year": 2020, "isbn": "111-1111111111"}
    response = client.post("/books", json=book_data)
    assert response.status_code == 201

    update_data = {"title": "Updated Title", "year": 2024}
    response = client.put("/books/1", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Original Author"  # Unchanged
    assert data["year"] == 2024


def test_delete_book_not_found(client):
    """Test deleting a non-existent book."""
    response = client.delete("/books/999")
    assert response.status_code == 404


def test_delete_book(client):
    """Test deleting an existing book."""
    book_data = {"title": "To Delete", "author": "Delete Author", "year": 2020, "isbn": "111-1111111111"}
    response = client.post("/books", json=book_data)
    assert response.status_code == 201

    response = client.delete("/books/1")
    assert response.status_code == 204

    # Verify book is deleted
    response = client.get("/books/1")
    assert response.status_code == 404


def test_multiple_books_operations(client):
    """Test a sequence of operations on books."""
    # Create multiple books
    books_data = [
        {"title": "Book A", "author": "Author X", "year": 2020},
        {"title": "Book B", "author": "Author Y", "year": 2021},
        {"title": "Book C", "author": "Author X", "year": 2022},
    ]

    for book_data in books_data:
        response = client.post("/books", json=book_data)
        assert response.status_code == 201

    # List all books
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Filter by author
    response = client.get("/books?author=Author%20X")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Update a book
    response = client.put("/books/1", json={"title": "Book A Updated"})
    assert response.status_code == 200
    assert response.json()["title"] == "Book A Updated"

    # Delete a book
    response = client.delete("/books/2")
    assert response.status_code == 204

    # Verify deletion
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
