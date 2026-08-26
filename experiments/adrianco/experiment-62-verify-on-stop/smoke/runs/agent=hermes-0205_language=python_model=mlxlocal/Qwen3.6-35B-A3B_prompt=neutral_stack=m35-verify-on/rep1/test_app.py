"""Comprehensive tests for the Book API REST service."""

import json
import os

import pytest

from app import create_app


@pytest.fixture
def client():
    """Create a test client with an in-memory SQLite database."""
    # Set env var BEFORE calling create_app so it picks up the in-memory DB
    old_db = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    app = create_app()

    with app.test_client() as client:
        yield client

    # Restore original env var
    if old_db is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = old_db


@pytest.fixture
def sample_book():
    """Return a sample book payload."""
    return {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "9780743273565",
    }


# --- Health Check ---

class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the health endpoint exists, when I call it, then I get 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"


# --- Create Book ---

class TestCreateBook:
    """Test creating a new book."""

    def test_create_book_success(self, client, sample_book):
        """Given valid data, when I POST /books, then the book is created with 201."""
        response = client.post(
            "/books",
            data=json.dumps(sample_book),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["title"] == sample_book["title"]
        assert data["author"] == sample_book["author"]
        assert data["year"] == sample_book["year"]
        assert data["isbn"] == sample_book["isbn"]
        assert "id" in data

    def test_create_book_missing_title(self, client):
        """Given missing title, when I POST /books, then I get 400."""
        payload = {"author": "Jane Austen", "year": 1813}
        response = client.post(
            "/books",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given missing author, when I POST /books, then I get 400."""
        payload = {"title": "Pride and Prejudice", "year": 1813}
        response = client.post(
            "/books",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_create_book_with_minimal_fields(self, client):
        """Given only required fields, when I POST /books, then the book is created."""
        payload = {"title": "1984", "author": "George Orwell"}
        response = client.post(
            "/books",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["title"] == "1984"
        assert data["year"] is None
        assert data["isbn"] is None

    def test_create_book_empty_json(self, client):
        """Given empty JSON, when I POST /books, then I get 400."""
        response = client.post(
            "/books",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400


# --- List Books ---

class TestListBooks:
    """Test listing books."""

    def test_list_books_empty(self, client):
        """Given no books, when I GET /books, then I get an empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client, sample_book):
        """Given books exist, when I GET /books, then I get the list."""
        client.post(
            "/books",
            data=json.dumps(sample_book),
            content_type="application/json",
        )
        response = client.get("/books")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["title"] == sample_book["title"]

    def test_list_books_filter_by_author(self, client):
        """Given multiple books, when I filter by author, then I get matching books."""
        book1 = {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925}
        book2 = {"title": "Pride and Prejudice", "author": "Jane Austen", "year": 1813}
        book3 = {"title": "The Crack-Up", "author": "F. Scott Fitzgerald", "year": 1936}

        for b in [book1, book2, book3]:
            client.post(
                "/books",
                data=json.dumps(b),
                content_type="application/json",
            )

        response = client.get("/books?author=Fitzgerald")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        assert all(d["author"] == "F. Scott Fitzgerald" for d in data)


# --- Get Book ---

class TestGetBook:
    """Test getting a single book."""

    def test_get_book_success(self, client, sample_book):
        """Given a book exists, when I GET /books/{id}, then I get the book."""
        resp = client.post(
            "/books",
            data=json.dumps(sample_book),
            content_type="application/json",
        )
        book_id = json.loads(resp.data)["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["id"] == book_id
        assert data["title"] == sample_book["title"]

    def test_get_book_not_found(self, client):
        """Given a non-existent book, when I GET /books/{id}, then I get 404."""
        response = client.get("/books/9999")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data


# --- Update Book ---

class TestUpdateBook:
    """Test updating a book."""

    def test_update_book_success(self, client, sample_book):
        """Given a book exists, when I PUT /books/{id}, then the book is updated."""
        resp = client.post(
            "/books",
            data=json.dumps(sample_book),
            content_type="application/json",
        )
        book_id = json.loads(resp.data)["id"]

        update_data = {"title": "Updated Title", "year": 2000}
        response = client.put(
            f"/books/{book_id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["title"] == "Updated Title"
        assert data["year"] == 2000
        assert data["author"] == sample_book["author"]  # unchanged

    def test_update_book_not_found(self, client):
        """Given a non-existent book, when I PUT /books/{id}, then I get 404."""
        response = client.put(
            "/books/9999",
            data=json.dumps({"title": "X"}),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_update_book_empty_title(self, client, sample_book):
        """Given empty title in update, when I PUT /books/{id}, then I get 400."""
        resp = client.post(
            "/books",
            data=json.dumps(sample_book),
            content_type="application/json",
        )
        book_id = json.loads(resp.data)["id"]

        response = client.put(
            f"/books/{book_id}",
            data=json.dumps({"title": ""}),
            content_type="application/json",
        )
        assert response.status_code == 400


# --- Delete Book ---

class TestDeleteBook:
    """Test deleting a book."""

    def test_delete_book_success(self, client, sample_book):
        """Given a book exists, when I DELETE /books/{id}, then it is removed."""
        resp = client.post(
            "/books",
            data=json.dumps(sample_book),
            content_type="application/json",
        )
        book_id = json.loads(resp.data)["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data

        # Verify it is gone
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a non-existent book, when I DELETE /books/{id}, then I get 404."""
        response = client.delete("/books/9999")
        assert response.status_code == 404
