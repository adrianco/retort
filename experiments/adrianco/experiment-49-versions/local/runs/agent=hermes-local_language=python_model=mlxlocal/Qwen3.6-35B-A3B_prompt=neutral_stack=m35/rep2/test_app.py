import os
import sys
import tempfile
import pytest

# Ensure the app module can be imported from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    app_module.app.config["TESTING"] = True

    # Use a temporary database file for tests
    fd, tmp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    original_db = app_module.DATABASE
    app_module.DATABASE = tmp_db

    # Re-initialize the database with the temp file
    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    # Clean up
    os.unlink(tmp_db)
    app_module.DATABASE = original_db


# --- Health check ---

class TestHealthCheck:
    def test_health_returns_ok(self, client):
        """Given the app is running, When I hit /health, Then I get a 200 with status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


# --- Create a book ---

class TestCreateBook:
    def test_create_book_success(self, client):
        """Given no books exist, When I POST a valid book, Then I get 201 with the book."""
        payload = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565",
        }
        response = client.post("/books", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "978-0743273565"
        assert "id" in data

    def test_create_book_minimal(self, client):
        """Given no books exist, When I POST title+author only, Then I get 201."""
        payload = {"title": "1984", "author": "George Orwell"}
        response = client.post("/books", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "1984"
        assert data["year"] is None

    def test_create_book_missing_title(self, client):
        """When I POST without title, Then I get 400."""
        payload = {"author": "Jane Austen"}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """When I POST without author, Then I get 400."""
        payload = {"title": "Pride and Prejudice"}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_empty_title(self, client):
        """When I POST with empty title, Then I get 400."""
        payload = {"title": "", "author": "Someone"}
        response = client.post("/books", json=payload)
        assert response.status_code == 400

    def test_create_book_invalid_year(self, client):
        """When I POST with non-integer year, Then I get 400."""
        payload = {"title": "Test", "author": "Author", "year": "not-a-number"}
        response = client.post("/books", json=payload)
        assert response.status_code == 400


# --- List books ---

class TestListBooks:
    def test_list_empty(self, client):
        """Given no books, When I GET /books, Then I get an empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books(self, client):
        """Given two books exist, When I GET /books, Then I get both."""
        client.post("/books", json={"title": "Book A", "author": "Author X"})
        client.post("/books", json={"title": "Book B", "author": "Author X"})
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given three books by two authors, When I GET ?author=X, Then I get only X's books."""
        client.post("/books", json={"title": "Book 1", "author": "Alice"})
        client.post("/books", json={"title": "Book 2", "author": "Bob"})
        client.post("/books", json={"title": "Book 3", "author": "Alice"})
        response = client.get("/books?author=Alice")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert "alice" in book["author"].lower()


# --- Get a single book ---

class TestGetBook:
    def test_get_existing_book(self, client):
        """Given a book exists, When I GET /books/<id>, Then I get the book."""
        resp = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
        book_id = resp.get_json()["id"]
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Dune"

    def test_get_nonexistent_book(self, client):
        """When I GET a book that doesn't exist, Then I get 404."""
        response = client.get("/books/9999")
        assert response.status_code == 404


# --- Update a book ---

class TestUpdateBook:
    def test_update_book_success(self, client):
        """Given a book exists, When I PUT updated fields, Then I get the updated book."""
        resp = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965})
        book_id = resp.get_json()["id"]
        response = client.put(f"/books/{book_id}", json={"year": 1966})
        assert response.status_code == 200
        data = response.get_json()
        assert data["year"] == 1966
        assert data["title"] == "Dune"  # unchanged

    def test_update_nonexistent_book(self, client):
        """When I PUT a book that doesn't exist, Then I get 404."""
        response = client.put("/books/9999", json={"title": "New Title"})
        assert response.status_code == 404

    def test_update_book_empty_title(self, client):
        """When I PUT with empty title, Then I get 400."""
        resp = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
        book_id = resp.get_json()["id"]
        response = client.put(f"/books/{book_id}", json={"title": ""})
        assert response.status_code == 400


# --- Delete a book ---

class TestDeleteBook:
    def test_delete_book_success(self, client):
        """Given a book exists, When I DELETE it, Then I get 200 and it's gone."""
        resp = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
        book_id = resp.get_json()["id"]
        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        assert response.get_json()["message"] == "Book deleted successfully"
        # Verify it's actually gone
        get_resp = client.get(f"/books/{book_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_book(self, client):
        """When I DELETE a book that doesn't exist, Then I get 404."""
        response = client.delete("/books/9999")
        assert response.status_code == 404
