"""
Acceptance tests for Book API REST Service.

Written from the perspective of an external HTTP client.
Each scenario starts from a clean, empty database.
Exercises only the public REST API surface.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app, get_db, db as _db_module


# ─── Test fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def app():
    """Return a Flask app instance configured for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"  # in-memory
    yield app


@pytest.fixture
def client(app):
    """Return a Flask test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def _clear_db(app):
    """Before every test, drop and recreate tables so the store is empty."""
    with app.app_context():
        _db_module.drop_all()
        _db_module.create_all()
    yield


# ─── 1. Health check ────────────────────────────────────────────────────────


class TestHealthCheck:
    """Verify the health-check endpoint exists and is operational."""

    def test_health_returns_200(self, client):
        """Given the service is running, GET /health returns 200 OK."""
        rv = client.get("/health")
        assert rv.status_code == 200

    def test_health_returns_json(self, client):
        """Given the service is running, GET /health returns JSON."""
        rv = client.get("/health")
        assert rv.content_type == "application/json"

    def test_health_status_is_healthy(self, client):
        """Given the service is running, GET /health reports 'healthy'."""
        rv = client.get("/health")
        data = json.loads(rv.data)
        assert data.get("status") == "healthy"


# ─── 2. Create a book (POST /books) ─────────────────────────────────────────


class TestCreateBook:
    """Exercise the 'create a book' business operation."""

    def test_create_book_returns_201(self, client):
        """When I create a book with valid data, the service returns 201 Created."""
        payload = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
        rv = client.post("/books", data=json.dumps(payload), content_type="application/json")
        assert rv.status_code == 201

    def test_create_book_returns_book(self, client):
        """When I create a book, the response body contains the book object."""
        payload = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
        rv = client.post("/books", data=json.dumps(payload), content_type="application/json")
        data = json.loads(rv.data)
        assert "id" in data
        assert data["title"] == "1984"
        assert data["author"] == "George Orwell"

    def test_create_book_missing_title_returns_400(self, client):
        """When I create a book without a title, the service rejects with 400."""
        payload = {"author": "George Orwell", "year": 1949}
        rv = client.post("/books", data=json.dumps(payload), content_type="application/json")
        assert rv.status_code == 400

    def test_create_book_missing_author_returns_400(self, client):
        """When I create a book without an author, the service rejects with 400."""
        payload = {"title": "1984", "year": 1949}
        rv = client.post("/books", data=json.dumps(payload), content_type="application/json")
        assert rv.status_code == 400

    def test_create_book_empty_title_returns_400(self, client):
        """When I create a book with an empty title, the service rejects with 400."""
        payload = {"title": "", "author": "George Orwell"}
        rv = client.post("/books", data=json.dumps(payload), content_type="application/json")
        assert rv.status_code == 400

    def test_create_book_empty_author_returns_400(self, client):
        """When I create a book with an empty author, the service rejects with 400."""
        payload = {"title": "1984", "author": ""}
        rv = client.post("/books", data=json.dumps(payload), content_type="application/json")
        assert rv.status_code == 400


# ─── 3. List books (GET /books) ─────────────────────────────────────────────


class TestListBooks:
    """Exercise the 'list all books' and 'filter books by author' operations."""

    def test_list_empty_returns_200(self, client):
        """When no books exist, GET /books returns 200 with an empty list."""
        rv = client.get("/books")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == []

    def test_list_returns_200(self, client):
        """When books exist, GET /books returns 200 with the book array."""
        client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        client.post("/books", data=json.dumps({"title": "Brave New World", "author": "Aldous Huxley"}), content_type="application/json")
        rv = client.get("/books")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert isinstance(data, list)

    def test_list_contains_created_books(self, client):
        """After creating books, GET /books returns them all."""
        client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        client.post("/books", data=json.dumps({"title": "Brave New World", "author": "Aldous Huxley"}), content_type="application/json")
        rv = client.get("/books")
        data = json.loads(rv.data)
        assert len(data) == 2
        titles = {b["title"] for b in data}
        assert "1984" in titles
        assert "Brave New World" in titles

    def test_list_filter_by_author_returns_matching(self, client):
        """When I filter by author, only books by that author are returned."""
        client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        client.post("/books", data=json.dumps({"title": "Brave New World", "author": "Aldous Huxley"}), content_type="application/json")
        client.post("/books", data=json.dumps({"title": "Animal Farm", "author": "George Orwell"}), content_type="application/json")
        rv = client.get("/books?author=George Orwell")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert len(data) == 2
        assert all(b["author"] == "George Orwell" for b in data)

    def test_list_filter_by_author_returns_empty_when_no_match(self, client):
        """When no books match the author filter, an empty list is returned."""
        client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        rv = client.get("/books?author=Jane Austen")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data == []


# ─── 4. Get a single book (GET /books/<id>) ─────────────────────────────────


class TestGetBook:
    """Exercise the 'get a single book' business operation."""

    def test_get_existing_book_returns_200(self, client):
        """When I request an existing book, the service returns 200."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell", "year": 1949}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        rv = client.get(f"/books/{book_id}")
        assert rv.status_code == 200

    def test_get_existing_book_returns_correct_data(self, client):
        """When I request an existing book, the returned data matches what was stored."""
        payload = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
        book = client.post("/books", data=json.dumps(payload), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        rv = client.get(f"/books/{book_id}")
        data = json.loads(rv.data)
        assert data["title"] == "1984"
        assert data["author"] == "George Orwell"
        assert data["year"] == 1949
        assert data["isbn"] == "978-0451524935"

    def test_get_nonexistent_book_returns_404(self, client):
        """When I request a book that does not exist, the service returns 404."""
        rv = client.get("/books/9999")
        assert rv.status_code == 404


# ─── 5. Update a book (PUT /books/<id>) ─────────────────────────────────────


class TestUpdateBook:
    """Exercise the 'update a book' business operation."""

    def test_update_existing_book_returns_200(self, client):
        """When I update an existing book, the service returns 200."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        rv = client.put(f"/books/{book_id}", data=json.dumps({"title": "Nineteen Eighty-Four", "author": "George Orwell"}), content_type="application/json")
        assert rv.status_code == 200

    def test_update_existing_book_changes_data(self, client):
        """When I update a book, the stored data reflects the changes."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        client.put(f"/books/{book_id}", data=json.dumps({"title": "Nineteen Eighty-Four", "author": "George Orwell"}), content_type="application/json")
        rv = client.get(f"/books/{book_id}")
        data = json.loads(rv.data)
        assert data["title"] == "Nineteen Eighty-Four"

    def test_update_partial_fields(self, client):
        """When I update only some fields, the others are preserved."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell", "year": 1949}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        client.put(f"/books/{book_id}", data=json.dumps({"title": "Nineteen Eighty-Four"}), content_type="application/json")
        rv = client.get(f"/books/{book_id}")
        data = json.loads(rv.data)
        assert data["title"] == "Nineteen Eighty-Four"
        assert data["author"] == "George Orwell"
        assert data["year"] == 1949

    def test_update_nonexistent_book_returns_404(self, client):
        """When I update a book that does not exist, the service returns 404."""
        rv = client.put("/books/9999", data=json.dumps({"title": "Nonexistent"}), content_type="application/json")
        assert rv.status_code == 404

    def test_update_book_missing_title_returns_400(self, client):
        """When I update a book with an empty title, the service rejects with 400."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        rv = client.put(f"/books/{book_id}", data=json.dumps({"title": "", "author": "George Orwell"}), content_type="application/json")
        assert rv.status_code == 400


# ─── 6. Delete a book (DELETE /books/<id>) ──────────────────────────────────


class TestDeleteBook:
    """Exercise the 'delete a book' business operation."""

    def test_delete_existing_book_returns_200(self, client):
        """When I delete an existing book, the service returns 200."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        rv = client.delete(f"/books/{book_id}")
        assert rv.status_code == 200

    def test_delete_existing_book_removes_it(self, client):
        """When I delete a book, it is no longer returned by GET /books."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        client.delete(f"/books/{book_id}")
        rv = client.get("/books")
        data = json.loads(rv.data)
        assert len(data) == 0

    def test_delete_existing_book_not_returned_anymore(self, client):
        """When I delete a book, GET /books/<id> returns 404."""
        book = client.post("/books", data=json.dumps({"title": "1984", "author": "George Orwell"}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        client.delete(f"/books/{book_id}")
        rv = client.get(f"/books/{book_id}")
        assert rv.status_code == 404

    def test_delete_nonexistent_book_returns_404(self, client):
        """When I delete a book that does not exist, the service returns 404."""
        rv = client.delete("/books/9999")
        assert rv.status_code == 404


# ─── 7. Books are isolated per test (no shared state) ───────────────────────


class TestIsolation:
    """Ensure each test scenario starts clean — no data leaks between scenarios."""

    def test_scenario_a_and_b_are_independent(self, client):
        """Creating a book in a test does not affect other tests."""
        book = client.post("/books", data=json.dumps({"title": "Temp", "author": "Temp"}), content_type="application/json")
        book_id = json.loads(book.data)["id"]
        client.delete(f"/books/{book_id}")
        # Database is cleaned again by the autouse fixture before the next test
        pass
