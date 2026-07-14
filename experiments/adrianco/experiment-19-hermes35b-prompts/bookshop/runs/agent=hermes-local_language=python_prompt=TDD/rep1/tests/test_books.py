"""Tests for Book CRUD endpoints."""
import pytest


class TestListBooks:
    """Tests for GET /books endpoint."""

    def test_get_books_empty_list(self, app):
        """GET /books should return an empty list when no books exist."""
        _, client = app
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_books_content_type(self, app):
        """GET /books should return JSON content type."""
        _, client = app
        response = client.get("/books")
        assert response.content_type == "application/json"

    def test_get_books_filter_by_author(self, app):
        """GET /books?author= should filter books by author."""
        _, client = app
        # Create some books first
        client.post("/books", json={"title": "Book One", "author": "Author A", "year": 2020})
        client.post("/books", json={"title": "Book Two", "author": "Author B", "year": 2021})
        client.post("/books", json={"title": "Book Three", "author": "Author A", "year": 2022})

        response = client.get("/books?author=Author A")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert book["author"] == "Author A"

    def test_get_books_filter_partial_author(self, app):
        """GET /books?author should support partial match."""
        _, client = app
        client.post("/books", json={"title": "Book One", "author": "John Smith", "year": 2020})
        client.post("/books", json={"title": "Book Two", "author": "Jane Doe", "year": 2021})

        response = client.get("/books?author=John")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["author"] == "John Smith"

    def test_get_books_returns_all_when_no_filter(self, app):
        """GET /books without filter should return all books."""
        _, client = app
        client.post("/books", json={"title": "Book One", "author": "Author A"})
        client.post("/books", json={"title": "Book Two", "author": "Author B"})

        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_get_book_by_id(self, app):
        """GET /books/{id} should return a single book."""
        _, client = app
        response = client.post("/books", json={"title": "Test Book", "author": "Test Author", "year": 2023, "isbn": "1234567890"})
        data = response.get_json()
        book_id = data["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Test Book"
        assert data["author"] == "Test Author"
        assert data["year"] == 2023
        assert data["isbn"] == "1234567890"

    def test_get_book_by_id_not_found(self, app):
        """GET /books/{id} should return 404 for nonexistent book."""
        _, client = app
        response = client.get("/books/9999")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_create_book(self, app):
        """POST /books should create a new book and return 201."""
        _, client = app
        response = client.post("/books", json={
            "title": "New Book",
            "author": "New Author",
            "year": 2024,
            "isbn": "978-0-123456-78-9"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "New Book"
        assert data["author"] == "New Author"
        assert data["year"] == 2024
        assert data["isbn"] == "978-0-123456-78-9"
        assert "id" in data

    def test_create_book_without_title(self, app):
        """POST /books without title should return 400."""
        _, client = app
        response = client.post("/books", json={"author": "Test Author"})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_without_author(self, app):
        """POST /books without author should return 400."""
        _, client = app
        response = client.post("/books", json={"title": "Test Book"})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_with_minimal_data(self, app):
        """POST /books with only title and author should work."""
        _, client = app
        response = client.post("/books", json={"title": "Minimal Book", "author": "Minimal Author"})
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Minimal Book"
        assert data["author"] == "Minimal Author"

    def test_update_book(self, app):
        """PUT /books/{id} should update a book."""
        _, client = app
        response = client.post("/books", json={"title": "Old Title", "author": "Old Author"})
        book_id = response.get_json()["id"]

        response = client.put(f"/books/{book_id}", json={
            "title": "Updated Title",
            "author": "Updated Author",
            "year": 2025
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Updated Title"
        assert data["author"] == "Updated Author"

    def test_update_book_not_found(self, app):
        """PUT /books/{id} should return 404 for nonexistent book."""
        _, client = app
        response = client.put("/books/9999", json={"title": "Ghost"})
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_delete_book(self, app):
        """DELETE /books/{id} should delete a book."""
        _, client = app
        response = client.post("/books", json={"title": "To Delete", "author": "Delete Author"})
        book_id = response.get_json()["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

        # Verify it is actually deleted
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 404

    def test_delete_book_not_found(self, app):
        """DELETE /books/{id} should return 404 for nonexistent book."""
        _, client = app
        response = client.delete("/books/9999")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_create_book_with_all_fields(self, app):
        """POST /books should store all fields correctly."""
        _, client = app
        response = client.post("/books", json={
            "title": "Complete Book",
            "author": "Full Author",
            "year": 2023,
            "isbn": "0-00-000000-0"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Complete Book"
        assert data["author"] == "Full Author"
        assert data["year"] == 2023
        assert data["isbn"] == "0-00-000000-0"

    def test_list_books_after_delete(self, app):
        """GET /books should not return deleted books."""
        _, client = app
        r1 = client.post("/books", json={"title": "Keep", "author": "Auth A"})
        r2 = client.post("/books", json={"title": "Remove", "author": "Auth B"})
        book_id = r2.get_json()["id"]

        client.delete(f"/books/{book_id}")
        response = client.get("/books")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "Keep"
