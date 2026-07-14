import os
import sys
import tempfile
import pytest

# Ensure the app module can be imported from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    app_module.app.config["TESTING"] = True

    # Use a temporary database file for tests
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    original_db = app_module.DATABASE
    app_module.DATABASE = tmp_path

    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    os.unlink(tmp_path)
    app_module.DATABASE = original_db


# --- Health Check Tests ---

class TestHealthCheck:
    def test_health_returns_ok(self, client):
        """Given the application is running, when I call GET /health, then I get status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


# --- Create Book Tests ---

class TestCreateBook:
    def test_create_book_success(self, client):
        """Given no books exist, when I POST a valid book, then I get 201 with the book."""
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

    def test_create_book_missing_title(self, client):
        """Given no books exist, when I POST without title, then I get 400 error."""
        payload = {"author": "Someone", "year": 2000}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given no books exist, when I POST without author, then I get 400 error."""
        payload = {"title": "Some Book", "year": 2000}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_invalid_year(self, client):
        """Given no books exist, when I POST with non-integer year, then I get 400 error."""
        payload = {"title": "Some Book", "author": "Someone", "year": "not-a-number"}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_minimal(self, client):
        """Given no books exist, when I POST with only title and author, then I get 201."""
        payload = {"title": "Minimal Book", "author": "Author"}
        response = client.post("/books", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Minimal Book"
        assert data["year"] is None
        assert data["isbn"] is None


# --- List Books Tests ---

class TestListBooks:
    def test_list_books_empty(self, client):
        """Given no books exist, when I GET /books, then I get an empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_with_data(self, client):
        """Given two books exist, when I GET /books, then I get both books."""
        client.post("/books", json={"title": "Book A", "author": "Author X"})
        client.post("/books", json={"title": "Book B", "author": "Author X"})
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given three books by two authors, when I GET /books?author=X, then I get only X's books."""
        client.post("/books", json={"title": "Book A", "author": "Alice"})
        client.post("/books", json={"title": "Book B", "author": "Bob"})
        client.post("/books", json={"title": "Book C", "author": "Alice"})
        response = client.get("/books?author=Alice")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert book["author"] == "Alice"


# --- Get Single Book Tests ---

class TestGetBook:
    def test_get_existing_book(self, client):
        """Given a book exists, when I GET /books/{id}, then I get the book."""
        resp = client.post("/books", json={"title": "Test", "author": "Author"})
        book_id = resp.get_json()["id"]
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Test"

    def test_get_nonexistent_book(self, client):
        """Given no book with id 999, when I GET /books/999, then I get 404."""
        response = client.get("/books/999")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


# --- Update Book Tests ---

class TestUpdateBook:
    def test_update_book_success(self, client):
        """Given a book exists, when I PUT updated data, then I get the updated book."""
        resp = client.post("/books", json={"title": "Old Title", "author": "Old Author"})
        book_id = resp.get_json()["id"]
        response = client.put(
            f"/books/{book_id}",
            json={"title": "New Title", "author": "New Author", "year": 2024},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "New Title"
        assert data["author"] == "New Author"
        assert data["year"] == 2024

    def test_update_nonexistent_book(self, client):
        """Given no book with id 999, when I PUT /books/999, then I get 404."""
        response = client.put("/books/999", json={"title": "X"})
        assert response.status_code == 404

    def test_update_book_missing_title(self, client):
        """Given a book exists, when I PUT with empty title, then I get 400."""
        resp = client.post("/books", json={"title": "Old", "author": "Author"})
        book_id = resp.get_json()["id"]
        response = client.put(f"/books/{book_id}", json={"title": "", "author": "Author"})
        assert response.status_code == 400


# --- Delete Book Tests ---

class TestDeleteBook:
    def test_delete_book_success(self, client):
        """Given a book exists, when I DELETE /books/{id}, then I get 200 and it is gone."""
        resp = client.post("/books", json={"title": "To Delete", "author": "Author"})
        book_id = resp.get_json()["id"]
        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

        # Verify it is gone
        get_resp = client.get(f"/books/{book_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_book(self, client):
        """Given no book with id 999, when I DELETE /books/999, then I get 404."""
        response = client.delete("/books/999")
        assert response.status_code == 404
