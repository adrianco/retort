"""Acceptance tests for the Book Collection REST API.

Each test is independent and starts from a clean (empty) service.
Tests exercise the system only through its public REST API.
"""
import pytest
from fastapi.testclient import TestClient

from app import app
import models


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_db():
    """Each test gets a clean database."""
    models.delete_db()
    models.init_db()


@pytest.fixture
def client():
    """HTTP test client backed by FastAPI's TestClient."""
    return TestClient(app)


# ===================================================================
# Health check
# ===================================================================
class TestHealthCheck:
    """Acceptance test: the service is healthy."""

    def test_health_check_returns_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ===================================================================
# Create a book  (POST /books)
# ===================================================================
class TestCreateBook:
    """Acceptance test: I can create a new book in the collection."""

    def test_create_book_with_all_fields_returns_created(self, client: TestClient):
        payload = {
            "title": "The Pragmatic Programmer",
            "author": "David Thomas",
            "year": 1999,
            "isbn": "978-0135957059",
        }
        resp = client.post("/books", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "The Pragmatic Programmer"
        assert body["author"] == "David Thomas"
        assert body["year"] == 1999
        assert body["isbn"] == "978-0135957059"
        assert body["id"] is not None
        assert body["created_at"] is not None
        assert body["updated_at"] is not None

    def test_create_book_without_optional_fields_returns_created(self, client: TestClient):
        payload = {"title": "Clean Code", "author": "Robert C. Martin"}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Clean Code"
        assert body["year"] is None
        assert body["isbn"] is None

    def test_create_book_with_missing_title_returns_unprocessable(self, client: TestClient):
        payload = {"author": "Someone"}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 422

    def test_create_book_with_missing_author_returns_unprocessable(self, client: TestClient):
        payload = {"title": "Some Title"}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 422

    def test_create_book_with_empty_title_returns_unprocessable(self, client: TestClient):
        payload = {"title": "", "author": "Someone"}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 422

    def test_create_book_with_empty_author_returns_unprocessable(self, client: TestClient):
        payload = {"title": "Some Title", "author": ""}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 422


# ===================================================================
# List books  (GET /books)
# ===================================================================
class TestListBooks:
    """Acceptance test: I can list all books in the collection."""

    def test_list_books_on_empty_collection_returns_empty_list(self, client: TestClient):
        resp = client.get("/books")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_books_returns_all_created_books(self, client: TestClient):
        client.post("/books", json={"title": "Book A", "author": "Author A"})
        client.post("/books", json={"title": "Book B", "author": "Author B"})
        resp = client.get("/books")
        assert resp.status_code == 200
        books = resp.json()
        assert len(books) == 2

    def test_list_books_filtered_by_author_returns_matching_only(
        self, client: TestClient
    ):
        client.post("/books", json={"title": "A1", "author": "Alice"})
        client.post("/books", json={"title": "A2", "author": "Alice"})
        client.post("/books", json={"title": "B1", "author": "Bob"})
        resp = client.get("/books", params={"author": "Alice"})
        assert resp.status_code == 200
        books = resp.json()
        assert len(books) == 2
        for b in books:
            assert b["author"] == "Alice"

    def test_list_books_filtered_by_nonexistent_author_returns_empty_list(
        self, client: TestClient
    ):
        client.post("/books", json={"title": "X", "author": "Alice"})
        resp = client.get("/books", params={"author": "Bob"})
        assert resp.status_code == 200
        assert resp.json() == []


# ===================================================================
# Get a single book  (GET /books/{id})
# ===================================================================
class TestGetBook:
    """Acceptance test: I can retrieve a specific book by ID."""

    def test_get_existing_book_returns_book(self, client: TestClient):
        created = client.post(
            "/books",
            json={"title": "Grokking Algorithms", "author": "Aditya Bhargava"},
        )
        book_id = created.json()["id"]
        resp = client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Grokking Algorithms"
        assert body["author"] == "Aditya Bhargava"

    def test_get_nonexistent_book_returns_not_found(self, client: TestClient):
        resp = client.get("/books/9999")
        assert resp.status_code == 404


# ===================================================================
# Update a book  (PUT /books/{id})
# ===================================================================
class TestUpdateBook:
    """Acceptance test: I can update an existing book."""

    def test_update_book_changes_fields(self, client: TestClient):
        created = client.post(
            "/books",
            json={"title": "Old Title", "author": "Old Author", "year": 2000},
        )
        book_id = created.json()["id"]
        resp = client.put(
            f"/books/{book_id}",
            json={"title": "New Title", "year": 2020},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "New Title"
        assert body["author"] == "Old Author"
        assert body["year"] == 2020

    def test_update_nonexistent_book_returns_not_found(self, client: TestClient):
        resp = client.put("/books/9999", json={"title": "Ghost"})
        assert resp.status_code == 404

    def test_update_book_with_empty_title_returns_unprocessable(self, client: TestClient):
        created = client.post(
            "/books", json={"title": "Valid", "author": "Valid"}
        )
        book_id = created.json()["id"]
        resp = client.put(f"/books/{book_id}", json={"title": ""})
        assert resp.status_code == 422

    def test_update_book_with_empty_author_returns_unprocessable(self, client: TestClient):
        created = client.post(
            "/books", json={"title": "Valid", "author": "Valid"}
        )
        book_id = created.json()["id"]
        resp = client.put(f"/books/{book_id}", json={"author": ""})
        assert resp.status_code == 422


# ===================================================================
# Delete a book  (DELETE /books/{id})
# ===================================================================
class TestDeleteBook:
    """Acceptance test: I can delete a book from the collection."""

    def test_delete_existing_book_returns_no_content(self, client: TestClient):
        created = client.post(
            "/books", json={"title": "To Delete", "author": "Someone"}
        )
        book_id = created.json()["id"]
        resp = client.delete(f"/books/{book_id}")
        assert resp.status_code == 204

    def test_delete_existing_book_removes_it(self, client: TestClient):
        created = client.post(
            "/books", json={"title": "To Delete", "author": "Someone"}
        )
        book_id = created.json()["id"]
        client.delete(f"/books/{book_id}")
        resp = client.get("/books")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_delete_nonexistent_book_returns_not_found(self, client: TestClient):
        resp = client.delete("/books/9999")
        assert resp.status_code == 404
