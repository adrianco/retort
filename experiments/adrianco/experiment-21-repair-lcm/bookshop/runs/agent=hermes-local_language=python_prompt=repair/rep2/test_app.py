"""Tests for the Book Collection REST API."""

import os
import sys
import pytest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import models
from app import app


def make_test_db():
    """Create a temporary test database and return its path."""
    tmpfd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmpfd)
    models.init_db(tmp_path)
    # Patch the global path function so models uses the temp DB
    old_get_path = models.get_db_path
    models.get_db_path = lambda: tmp_path
    return tmp_path, old_get_path


@pytest.fixture(autouse=True)
def patch_db():
    """Patch models.get_db_path to use a temp DB for all tests."""
    tmp_path, old_get_path = make_test_db()
    yield tmp_path
    # Restore
    models.get_db_path = old_get_path
    # Clean up
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.fixture
def client(patch_db):
    """Create a Flask test client that uses the test database."""
    app.config["TESTING"] = True
    return app.test_client()


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """GET /health returns 200 with status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


class TestCreateBook:
    """Tests for creating books."""

    def test_create_book_success(self, client):
        """POST /books creates a book with valid data."""
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

    def test_create_book_without_optional_fields(self, client):
        """POST /books creates a book without year and isbn."""
        response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Dune"
        assert data["author"] == "Frank Herbert"
        assert data["year"] is None
        assert data["isbn"] is None

    def test_create_book_missing_title(self, client):
        """POST /books returns 400 when title is missing."""
        response = client.post("/books", json={"author": "Test Author"})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "title is required" in data["error"]

    def test_create_book_missing_author(self, client):
        """POST /books returns 400 when author is missing."""
        response = client.post("/books", json={"title": "Test Book"})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "author is required" in data["error"]


class TestListBooks:
    """Tests for listing books."""

    def test_list_books_empty(self, client):
        """GET /books returns empty list when no books exist."""
        response = client.get("/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_books_returns_all(self, client):
        """GET /books returns all books."""
        client.post("/books", json={"title": "Book A", "author": "Author X"})
        client.post("/books", json={"title": "Book B", "author": "Author Y"})
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """GET /books?author=X returns only books by that author."""
        client.post("/books", json={"title": "Book A", "author": "Author X"})
        client.post("/books", json={"title": "Book B", "author": "Author Y"})
        client.post("/books", json={"title": "Book C", "author": "Author X"})
        response = client.get("/books?author=Author+X")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert book["author"] == "Author X"


class TestGetBook:
    """Tests for getting a single book."""

    def test_get_book_existing(self, client):
        """GET /books/{id} returns the book."""
        response = client.post("/books", json={"title": "1984", "author": "George Orwell"})
        book_data = response.get_json()
        book_id = book_data["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "1984"
        assert data["author"] == "George Orwell"

    def test_get_book_not_found(self, client):
        """GET /books/{id} returns 404 for non-existent book."""
        response = client.get("/books/9999")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestUpdateBook:
    """Tests for updating books."""

    def test_update_book_success(self, client):
        """PUT /books/{id} updates the book."""
        response = client.post("/books", json={"title": "Original Title", "author": "Author"})
        book_data = response.get_json()
        book_id = book_data["id"]

        response = client.put(f"/books/{book_id}", json={"title": "Updated Title", "author": "Updated Author"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Updated Title"
        assert data["author"] == "Updated Author"

    def test_update_book_partial(self, client):
        """PUT /books/{id} updates only the provided fields."""
        response = client.post("/books", json={"title": "Original Title", "author": "Author"})
        book_data = response.get_json()
        book_id = book_data["id"]

        response = client.put(f"/books/{book_id}", json={"title": "Updated Title"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Updated Title"
        assert data["author"] == "Author"

    def test_update_book_not_found(self, client):
        """PUT /books/{id} returns 404 for non-existent book."""
        response = client.put("/books/9999", json={"title": "New Title"})
        assert response.status_code == 404


class TestDeleteBook:
    """Tests for deleting books."""

    def test_delete_book_success(self, client):
        """DELETE /books/{id} deletes the book and returns 200."""
        response = client.post("/books", json={"title": "To Delete", "author": "Author"})
        book_data = response.get_json()
        book_id = book_data["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

        # Verify it's actually deleted
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 404

    def test_delete_book_not_found(self, client):
        """DELETE /books/{id} returns 404 for non-existent book."""
        response = client.delete("/books/9999")
        assert response.status_code == 404
