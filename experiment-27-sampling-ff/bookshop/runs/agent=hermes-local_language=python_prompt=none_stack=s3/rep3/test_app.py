import os
import sys
import tempfile
import pytest

# Ensure the app module can be imported from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    app_module.app.config["TESTING"] = True

    # Use an in-memory database for tests
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    old_db = app_module.DATABASE
    app_module.DATABASE = db_path

    # Re-initialize the database with the test path
    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)
    app_module.DATABASE = old_db


# --- Health Check Tests ---

class TestHealthCheck:
    def test_health_check_returns_200(self, client):
        """Given the API is running, when I call GET /health, then it returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_healthy_status(self, client):
        """Given the API is running, when I call GET /health, then status is healthy."""
        response = client.get("/health")
        data = response.get_json()
        assert data["status"] == "healthy"


# --- Create Book Tests (POST /books) ---

class TestCreateBook:
    def test_create_book_success(self, client):
        """Given no books exist, when I POST a valid book, then it returns 201 with the book."""
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
        assert data["id"] is not None

    def test_create_book_missing_title(self, client):
        """Given no books exist, when I POST without title, then it returns 400."""
        payload = {"author": "Unknown", "year": 2000}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given no books exist, when I POST without author, then it returns 400."""
        payload = {"title": "Some Book", "year": 2000}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_minimal(self, client):
        """Given no books exist, when I POST with only title and author, then it returns 201."""
        payload = {"title": "Minimal Book", "author": "Author Name"}
        response = client.post("/books", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Minimal Book"
        assert data["year"] is None


# --- List Books Tests (GET /books) ---

class TestListBooks:
    def test_list_books_empty(self, client):
        """Given no books exist, when I GET /books, then it returns an empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_returns_all(self, client):
        """Given 3 books exist, when I GET /books, then it returns all of them."""
        for i in range(3):
            client.post("/books", json={
                "title": f"Book {i}",
                "author": f"Author {i}",
            })
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client):
        """Given multiple books by different authors, when I GET /books?author=Author1, then it returns only matching books."""
        client.post("/books", json={"title": "Book A", "author": "Alice"})
        client.post("/books", json={"title": "Book B", "author": "Bob"})
        client.post("/books", json={"title": "Book C", "author": "Alice"})
        response = client.get("/books?author=Alice")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert "Alice" in book["author"]


# --- Get Book Tests (GET /books/<id>) ---

class TestGetBook:
    def test_get_book_not_found(self, client):
        """Given no books exist, when I GET /books/999, then it returns 404."""
        response = client.get("/books/999")
        assert response.status_code == 404

    def test_get_book_success(self, client):
        """Given a book exists, when I GET /books/1, then it returns the book."""
        resp = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author",
        })
        book_id = resp.get_json()["id"]
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Test Book"


# --- Update Book Tests (PUT /books/<id>) ---

class TestUpdateBook:
    def test_update_book_success(self, client):
        """Given a book exists, when I PUT updated data with title and author, then it returns the updated book."""
        resp = client.post("/books", json={
            "title": "Old Title",
            "author": "Old Author",
        })
        book_id = resp.get_json()["id"]
        response = client.put(f"/books/{book_id}", json={
            "title": "New Title",
            "author": "Old Author",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "New Title"
        assert data["author"] == "Old Author"

    def test_update_book_not_found(self, client):
        """Given no books exist, when I PUT /books/999, then it returns 404."""
        response = client.put("/books/999", json={"title": "New", "author": "Author"})
        assert response.status_code == 404

    def test_update_book_missing_title(self, client):
        """Given a book exists, when I PUT without title, then it returns 400."""
        resp = client.post("/books", json={
            "title": "Old Title",
            "author": "Old Author",
        })
        book_id = resp.get_json()["id"]
        response = client.put(f"/books/{book_id}", json={"author": "New Author"})
        assert response.status_code == 400


# --- Delete Book Tests (DELETE /books/<id>) ---

class TestDeleteBook:
    def test_delete_book_success(self, client):
        """Given a book exists, when I DELETE /books/1, then it returns 200 and the book is gone."""
        resp = client.post("/books", json={
            "title": "To Delete",
            "author": "Author",
        })
        book_id = resp.get_json()["id"]
        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_resp = client.get(f"/books/{book_id}")
        assert get_resp.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given no books exist, when I DELETE /books/999, then it returns 404."""
        response = client.delete("/books/999")
        assert response.status_code == 404
