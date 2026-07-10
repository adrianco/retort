"""
Acceptance Tests for Book API REST Service

All tests are written from the perspective of an external client exercising
the service through its REST API only.  Each test is atomic and independent -
each scenario starts from a fresh, empty service.
"""
import os
import pytest


@pytest.fixture
def client():
    """Create a fresh test client for each test."""
    os.environ["DATABASE_URI"] = "sqlite:///:memory:"

    from app import create_app, db

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as testing_client:
        with app.app_context():
            db.create_all()
        yield testing_client
        # teardown: drop everything so next test starts clean
        with app.app_context():
            db.drop_all()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Verify the health-check endpoint is available and responds."""

    def test_health_check_returns_200(self, client):
        """GET /health returns HTTP 200 when the service is healthy."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_json(self, client):
        """GET /health returns a JSON body with status information."""
        response = client.get("/health")
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Create a book
# ---------------------------------------------------------------------------

class TestCreateBook:
    """POST /books - create a new book in the collection."""

    def test_create_book_succeeds(self, client):
        """A well-formed POST /books returns 201 and includes the created book."""
        payload = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565",
        }
        response = client.post(
            "/books",
            data=payload,
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "978-0743273565"
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_create_book_generates_unique_id(self, client):
        """Each created book receives a unique auto-incrementing ID."""
        payload_a = {
            "title": "Book A",
            "author": "Author A",
            "year": 2000,
            "isbn": "111",
        }
        payload_b = {
            "title": "Book B",
            "author": "Author A",
            "year": 2001,
            "isbn": "222",
        }
        resp_a = client.post("/books", json=payload_a)
        resp_b = client.post("/books", json=payload_b)
        assert resp_a.get_json()["id"] != resp_b.get_json()["id"]

    def test_create_book_missing_title_returns_400(self, client):
        """POST /books without a title returns 400 Bad Request."""
        payload = {"author": "Anonymous", "year": 2020, "isbn": "000"}
        response = client.post(
            "/books",
            data=payload,
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_missing_author_returns_400(self, client):
        """POST /books without an author returns 400 Bad Request."""
        payload = {"title": "Some Book", "year": 2020, "isbn": "000"}
        response = client.post(
            "/books",
            data=payload,
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_empty_title_and_author_returns_400(self, client):
        """POST /books with empty strings for title/author returns 400."""
        payload = {"title": "", "author": "", "year": 2020, "isbn": "000"}
        response = client.post(
            "/books",
            data=payload,
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_create_book_year_optional(self, client):
        """POST /books without year or isbn still succeeds (they are optional)."""
        payload = {"title": "Minimal Book", "author": "Min Author"}
        response = client.post(
            "/books",
            data=payload,
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Minimal Book"
        assert data["author"] == "Min Author"
        assert data["year"] is None
        assert data["isbn"] is None


# ---------------------------------------------------------------------------
# List all books
# ---------------------------------------------------------------------------

class TestListBooks:
    """GET /books - list books in the collection."""

    def test_list_books_empty_returns_200(self, client):
        """GET /books on an empty collection returns 200 with an empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_returns_created_books(self, client):
        """GET /books returns all books that have been created."""
        client.post("/books", data={"title": "A", "author": "B", "year": 2000}, content_type="application/json")
        client.post("/books", data={"title": "C", "author": "D", "year": 2001}, content_type="application/json")
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        titles = {b["title"] for b in data}
        assert titles == {"A", "C"}

    def test_list_books_filtered_by_author(self, client):
        """GET /books?author= filters the collection to only matching authors."""
        client.post("/books", data={"title": "Alpha", "author": "Alice", "year": 2000}, content_type="application/json")
        client.post("/books", data={"title": "Beta", "author": "Bob", "year": 2001}, content_type="application/json")
        client.post("/books", data={"title": "Gamma", "author": "Alice", "year": 2002}, content_type="application/json")
        response = client.get("/books?author=Alice")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert book["author"] == "Alice"

    def test_list_books_no_author_param_returns_all(self, client):
        """GET /books without author filter returns the full collection."""
        client.post("/books", data={"title": "X", "author": "Y", "year": 2020}, content_type="application/json")
        client.post("/books", data={"title": "Z", "author": "W", "year": 2021}, content_type="application/json")
        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2


# ---------------------------------------------------------------------------
# Get a single book
# ---------------------------------------------------------------------------

class TestGetBook:
    """GET /books/{id} - retrieve a specific book."""

    def test_get_existing_book_returns_200(self, client):
        """GET /books/{id} for a known book returns 200 and the book details."""
        resp = client.post(
            "/books",
            data={"title": "Test Book", "author": "Test Author", "year": 2020, "isbn": "555"},
            content_type="application/json",
        )
        book_id = resp.get_json()["id"]
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Test Book"
        assert data["author"] == "Test Author"
        assert data["year"] == 2020
        assert data["isbn"] == "555"

    def test_get_nonexistent_book_returns_404(self, client):
        """GET /books/{id} for an unknown ID returns 404 Not Found."""
        response = client.get("/books/99999")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_get_book_returns_all_fields(self, client):
        """GET /books/{id} returns all stored fields including optional ones."""
        resp = client.post(
            "/books",
            data={"title": "Full Book", "author": "Full Author", "year": 2010, "isbn": "123-456"},
            content_type="application/json",
        )
        book_id = resp.get_json()["id"]
        response = client.get(f"/books/{book_id}")
        data = response.get_json()
        assert data["id"] is not None
        assert data["title"] == "Full Book"
        assert data["author"] == "Full Author"
        assert data["year"] == 2010
        assert data["isbn"] == "123-456"


# ---------------------------------------------------------------------------
# Update a book
# ---------------------------------------------------------------------------

class TestUpdateBook:
    """PUT /books/{id} - update an existing book."""

    def test_update_book_succeeds(self, client):
        """PUT /books/{id} with valid data returns 200 and the updated book."""
        resp = client.post(
            "/books",
            data={"title": "Old Title", "author": "Old Author", "year": 2000},
            content_type="application/json",
        )
        book_id = resp.get_json()["id"]
        update_payload = {
            "title": "New Title",
            "author": "New Author",
            "year": 2025,
        }
        response = client.put(
            f"/books/{book_id}",
            data=update_payload,
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "New Title"
        assert data["author"] == "New Author"
        assert data["year"] == 2025

    def test_update_book_preserves_id(self, client):
        """PUT /books/{id} does not change the book's ID."""
        resp = client.post(
            "/books",
            data={"title": "Preserved", "author": "ID", "year": 2000},
            content_type="application/json",
        )
        book_id = resp.get_json()["id"]
        client.put(
            f"/books/{book_id}",
            data={"title": "Updated Title", "author": "Updated Author"},
            content_type="application/json",
        )
        get_resp = client.get(f"/books/{book_id}")
        assert get_resp.get_json()["id"] == book_id

    def test_update_nonexistent_book_returns_404(self, client):
        """PUT /books/{id} for an unknown ID returns 404."""
        response = client.put(
            "/books/99999",
            data={"title": "Ghost", "author": "Ghost"},
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_update_partial_fields(self, client):
        """PUT /books/{id} with only some fields updates only those fields."""
        resp = client.post(
            "/books",
            data={"title": "Original", "author": "Original Author", "year": 2000, "isbn": "111"},
            content_type="application/json",
        )
        book_id = resp.get_json()["id"]
        response = client.put(
            f"/books/{book_id}",
            data={"title": "New Title"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "New Title"
        assert data["author"] == "Original Author"
        assert data["year"] == 2000
        assert data["isbn"] == "111"


# ---------------------------------------------------------------------------
# Delete a book
# ---------------------------------------------------------------------------

class TestDeleteBook:
    """DELETE /books/{id} - remove a book from the collection."""

    def test_delete_book_succeeds(self, client):
        """DELETE /books/{id} for a known book returns 200 and the book is removed."""
        resp = client.post(
            "/books",
            data={"title": "To Delete", "author": "Author", "year": 2020},
            content_type="application/json",
        )
        book_id = resp.get_json()["id"]
        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        # Verify the book is gone
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_book_returns_404(self, client):
        """DELETE /books/{id} for an unknown ID returns 404."""
        response = client.delete("/books/99999")
        assert response.status_code == 404

    def test_delete_book_removes_from_list(self, client):
        """After DELETE /books/{id}, the book no longer appears in GET /books."""
        resp = client.post(
            "/books",
            data={"title": "Vanish", "author": "Author", "year": 2020},
            content_type="application/json",
        )
        book_id = resp.get_json()["id"]
        client.delete(f"/books/{book_id}")
        response = client.get("/books")
        data = response.get_json()
        assert len(data) == 0


# ---------------------------------------------------------------------------
# Integration scenario: full CRUD lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:
    """End-to-end scenario exercising the complete book lifecycle."""

    def test_create_read_update_delete_lifecycle(self, client):
        """Create a book, read it, update it, delete it - all through the API."""
        # CREATE
        resp_create = client.post(
            "/books",
            data={
                "title": "War and Peace",
                "author": "Leo Tolstoy",
                "year": 1869,
                "isbn": "978-0199232765",
            },
            content_type="application/json",
        )
        assert resp_create.status_code == 201
        book_id = resp_create.get_json()["id"]
        assert book_id is not None

        # READ
        resp_read = client.get(f"/books/{book_id}")
        assert resp_read.status_code == 200
        assert resp_read.get_json()["title"] == "War and Peace"

        # UPDATE
        resp_update = client.put(
            f"/books/{book_id}",
            data={"year": 1869},
            content_type="application/json",
        )
        assert resp_update.status_code == 200
        updated = resp_update.get_json()
        assert updated["year"] == 1869
        assert updated["id"] == book_id

        # DELETE
        resp_delete = client.delete(f"/books/{book_id}")
        assert resp_delete.status_code == 200

        # Verify gone
        resp_gone = client.get(f"/books/{book_id}")
        assert resp_gone.status_code == 404

    def test_filter_by_author_across_operations(self, client):
        """After multiple create/update/delete operations, author filter is accurate."""
        client.post("/books", data={"title": "Book 1", "author": "Tolkien", "year": 1954}, content_type="application/json")
        client.post("/books", data={"title": "Book 2", "author": "Orwell", "year": 1949}, content_type="application/json")
        client.post("/books", data={"title": "Book 3", "author": "Tolkien", "year": 1951}, content_type="application/json")

        resp = client.get("/books?author=Tolkien")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2

        # Delete one Tolkien book
        tolc = resp.get_json()[0]
        client.delete(f"/books/{tolc['id']}")

        # Filter again
        resp = client.get("/books?author=Tolkien")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1
