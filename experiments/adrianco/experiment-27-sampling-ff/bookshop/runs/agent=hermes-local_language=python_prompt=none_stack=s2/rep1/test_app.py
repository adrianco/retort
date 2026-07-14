import os
import sys
import tempfile
import pytest

# Ensure the app module can be imported from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture(autouse=True)
def clean_db():
    """Remove and reinitialize the database before each test."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    app_module.init_db()


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


# --- Health Check Tests ---

class TestHealthCheck:
    def test_health_returns_ok(self, client):
        """Given the health endpoint exists, when called, then it returns 200 with status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


# --- Create Book Tests ---

class TestCreateBook:
    def test_create_book_success(self, client):
        """Given valid book data, when POST /books is called, then a new book is created with 201."""
        response = client.post(
            "/books",
            json={"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "978-0743273565"
        assert data["id"] is not None

    def test_create_book_missing_title(self, client):
        """Given missing title, when POST /books is called, then it returns 400 with error."""
        response = client.post("/books", json={"author": "Some Author"})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given missing author, when POST /books is called, then it returns 400 with error."""
        response = client.post("/books", json={"title": "Some Title"})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_no_body(self, client):
        """Given no request body, when POST /books is called, then it returns 415 (unsupported media type)."""
        response = client.post("/books", json=None)
        assert response.status_code == 415


# --- List Books Tests ---

class TestListBooks:
    def test_list_books_empty(self, client):
        """Given no books exist, when GET /books is called, then it returns an empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_books_with_filter(self, client):
        """Given multiple books exist, when GET /books?author=filter is called, then only matching books are returned."""
        # Create two books by different authors
        client.post("/books", json={"title": "Book A", "author": "Author One"})
        client.post("/books", json={"title": "Book B", "author": "Author Two"})
        client.post("/books", json={"title": "Book C", "author": "Author One"})

        response = client.get("/books?author=One")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert "One" in book["author"]


# --- Get Single Book Tests ---

class TestGetBook:
    def test_get_book_success(self, client):
        """Given a book exists, when GET /books/{id} is called, then the book is returned."""
        create_resp = client.post("/books", json={"title": "1984", "author": "George Orwell"})
        book_id = create_resp.get_json()["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "1984"

    def test_get_book_not_found(self, client):
        """Given a book does not exist, when GET /books/{id} is called, then it returns 404."""
        response = client.get("/books/999")
        assert response.status_code == 404


# --- Update Book Tests ---

class TestUpdateBook:
    def test_update_book_success(self, client):
        """Given a book exists, when PUT /books/{id} is called with new data, then the book is updated."""
        create_resp = client.post("/books", json={"title": "Original Title", "author": "Original Author"})
        book_id = create_resp.get_json()["id"]

        response = client.put(
            f"/books/{book_id}",
            json={"title": "Updated Title", "author": "Updated Author", "year": 2024},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Updated Title"
        assert data["author"] == "Updated Author"
        assert data["year"] == 2024

    def test_update_book_not_found(self, client):
        """Given a book does not exist, when PUT /books/{id} is called, then it returns 404."""
        response = client.put("/books/999", json={"title": "New Title"})
        assert response.status_code == 404


# --- Delete Book Tests ---

class TestDeleteBook:
    def test_delete_book_success(self, client):
        """Given a book exists, when DELETE /books/{id} is called, then the book is deleted."""
        create_resp = client.post("/books", json={"title": "To Delete", "author": "Author"})
        book_id = create_resp.get_json()["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a book does not exist, when DELETE /books/{id} is called, then it returns 404."""
        response = client.delete("/books/999")
        assert response.status_code == 404
