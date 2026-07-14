"""
BDD-style acceptance tests for the Book API REST Service.

Each test is structured as a Given-When-Then scenario that exercises the
system through its public HTTP interface, so the test suite reads as a
specification of what the service does from an external client perspective.
"""

import json
import os
import tempfile

import pytest

from app import app


@pytest.fixture(autouse=True)
def client():
    """Set up a fresh test client with a clean SQLite database per scenario.

    Each test gets its own isolated database so scenarios do not leak state.
    Yields the Flask test client for use in tests.
    """
    app.config["TESTING"] = True

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    app.config["BOOK_DB_PATH"] = tmp.name
    import app as app_module

    app_module.DB_PATH = tmp.name
    app_module.init_db()

    test_client = app.test_client()

    yield test_client

    import app as app_module
    app_module.DB_PATH = os.environ.get("BOOK_DB_PATH", "books.db")
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Feature: Health Check
# ---------------------------------------------------------------------------
class TestHealthCheck:
    """Feature: Health Check -- the service reports its availability."""

    def test_health_endpoint_returns_200_with_healthy_status(self, client):
        """Scenario: Health check succeeds

        Given the service is running
        When I send a GET request to /health
        Then I receive a 200 OK response with status "healthy"
        """
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# Feature: Create a Book
# ---------------------------------------------------------------------------
class TestCreateBook:
    """Feature: Create a Book -- clients can add new books to the collection."""

    def test_create_book_succeeds_with_valid_data(self, client):
        """Scenario: Add a book with complete data

        Given the catalogue is empty
        When I POST a book with title, author, year, and isbn
        Then the response is 201 Created with the book including a generated id
        """
        payload = {
            "title": "1984",
            "author": "George Orwell",
            "year": 1949,
            "isbn": "978-0451524935",
        }
        resp = client.post("/books", json=payload)
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["title"] == "1984"
        assert data["author"] == "George Orwell"
        assert data["year"] == 1949
        assert data["isbn"] == "978-0451524935"
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["id"] > 0

    def test_create_book_succeeds_with_required_fields_only(self, client):
        """Scenario: Add a book with minimal required fields

        Given the catalogue is empty
        When I POST a book with only title and author
        Then the book is stored and returned with generated id and year/isbn as null
        """
        payload = {"title": "Moby Dick", "author": "Herman Melville"}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["id"] is not None
        assert data["title"] == "Moby Dick"
        assert data["year"] is None
        assert data["isbn"] is None

    def test_create_book_fails_when_title_is_missing(self, client):
        """Scenario: Create a book without title

        Given the catalogue is empty
        When I POST a book with only author (missing title)
        Then I receive a 400 Bad Request with an error message
        """
        payload = {"author": "Jane Austen"}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_create_book_fails_when_author_is_missing(self, client):
        """Scenario: Create a book without author

        Given the catalogue is empty
        When I POST a book with only title (missing author)
        Then I receive a 400 Bad Request with an error message
        """
        payload = {"title": "Pride and Prejudice"}
        resp = client.post("/books", json=payload)
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_create_book_fails_when_body_is_empty(self, client):
        """Scenario: Create a book with an empty body

        Given the catalogue is empty
        When I POST to /books with no JSON body
        Then I receive a 400 Bad Request
        """
        resp = client.post("/books", content_type="application/json", data="")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Feature: List Books
# ---------------------------------------------------------------------------
class TestListBooks:
    """Feature: List Books -- clients can retrieve the full collection or filter by author."""

    def test_list_books_empty_when_no_books_exist(self, client):
        """Scenario: List books when the catalogue is empty

        Given no books have been added yet
        When I GET /books
        Then I receive a 200 OK with an empty array
        """
        resp = client.get("/books")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []

    def test_list_books_returns_all_books(self, client):
        """Scenario: List all books

        Given three books by two different authors exist
        When I GET /books without any filters
        Then I receive a 200 OK with all three books
        """
        for book_data in [
            {"title": "1984", "author": "George Orwell", "year": 1949},
            {"title": "Animal Farm", "author": "George Orwell", "year": 1945},
            {"title": "Brave New World", "author": "Aldous Huxley", "year": 1932},
        ]:
            client.post("/books", json=book_data)

        resp = client.get("/books")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 3

    def test_list_books_filtered_by_exact_author(self, client):
        """Scenario: Filter books by author

        Given three books by two different authors exist
        When I GET /books?author=George Orwell
        Then only the two books by George Orwell are returned
        """
        for book_data in [
            {"title": "1984", "author": "George Orwell", "year": 1949},
            {"title": "Animal Farm", "author": "George Orwell", "year": 1945},
            {"title": "Brave New World", "author": "Aldous Huxley", "year": 1932},
        ]:
            client.post("/books", json=book_data)

        resp = client.get("/books?author=George Orwell")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 2
        for book in data:
            assert "Orwell" in book["author"]

    def test_list_books_filtered_by_partial_author(self, client):
        """Scenario: Filter books by partial author name

        Given three books by three different authors exist
        When I GET /books?author=Aldous
        Then only the one book by an author containing "Aldous" is returned
        """
        for book_data in [
            {"title": "1984", "author": "George Orwell", "year": 1949},
            {"title": "Brave New World", "author": "Aldous Huxley", "year": 1932},
            {"title": "Fahrenheit 451", "author": "Ray Bradbury", "year": 1953},
        ]:
            client.post("/books", json=book_data)

        resp = client.get("/books?author=Aldous")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]["title"] == "Brave New World"

    def test_list_books_filter_with_no_matches(self, client):
        """Scenario: Filter books by a non-existent author

        Given three books by known authors exist
        When I GET /books?author=NonExistent
        Then I receive a 200 OK with an empty array
        """
        for book_data in [
            {"title": "1984", "author": "George Orwell", "year": 1949},
            {"title": "Brave New World", "author": "Aldous Huxley", "year": 1932},
        ]:
            client.post("/books", json=book_data)

        resp = client.get("/books?author=NonExistent")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []


# ---------------------------------------------------------------------------
# Feature: Get a Single Book
# ---------------------------------------------------------------------------
class TestGetBook:
    """Feature: Get a Single Book -- clients can retrieve an individual book by ID."""

    def test_get_book_returns_200_with_valid_id(self, client):
        """Scenario: Get an existing book by ID

        Given a book with title "Dune" and author "Frank Herbert" exists
        When I GET /books/1
        Then I receive a 200 OK with the book details
        """
        client.post(
            "/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965}
        )
        resp = client.get("/books/1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["title"] == "Dune"
        assert data["author"] == "Frank Herbert"
        assert data["year"] == 1965

    def test_get_book_returns_404_when_id_does_not_exist(self, client):
        """Scenario: Get a book that does not exist

        Given no books exist
        When I GET /books/999
        Then I receive a 404 Not Found with an error message
        """
        resp = client.get("/books/999")
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert "error" in data


# ---------------------------------------------------------------------------
# Feature: Update a Book
# ---------------------------------------------------------------------------
class TestUpdateBook:
    """Feature: Update a Book -- clients can modify an existing book."""

    def test_update_book_changes_fields(self, client):
        """Scenario: Update an existing book with new values

        Given a book exists with title "1984" and author "George Orwell"
        When I PUT /books/1 with a new title and year
        Then the book is updated and the response contains the new values
        """
        client.post(
            "/books",
            json={
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "isbn": "978-0451524935",
            },
        )
        resp = client.put(
            "/books/1",
            json={"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["title"] == "Nineteen Eighty-Four"
        assert data["author"] == "George Orwell"
        assert data["year"] == 1949

    def test_update_book_returns_404_for_nonexistent_id(self, client):
        """Scenario: Update a book that does not exist

        Given no books exist
        When I PUT /books/999
        Then I receive a 404 Not Found with an error message
        """
        resp = client.put("/books/999", json={"title": "New Title"})
        assert resp.status_code == 404

    def test_update_book_fails_without_title(self, client):
        """Scenario: Update a book missing the required title

        Given a book exists
        When I PUT /books/1 without a title in the body
        Then I receive a 400 Bad Request with an error message
        """
        client.post(
            "/books", json={"title": "Foundation", "author": "Isaac Asimov"}
        )
        resp = client.put("/books/1", json={"author": "Isaac Asimov"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Feature: Delete a Book
# ---------------------------------------------------------------------------
class TestDeleteBook:
    """Feature: Delete a Book -- clients can remove a book from the collection."""

    def test_delete_book_removes_it(self, client):
        """Scenario: Delete an existing book

        Given a book exists in the catalogue
        When I DELETE /books/1
        Then I receive a 200 OK with a confirmation message
        """
        client.post(
            "/books", json={"title": "The Great Gatsby", "author": "F. Scott Fitzgerald"}
        )
        resp = client.delete("/books/1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "message" in data

    def test_delete_book_prevents_it_from_appearing_in_list(self, client):
        """Scenario: Deleted book no longer appears in listings

        Given one book exists in the catalogue
        When I DELETE /books/1
        Then GET /books returns an empty list
        """
        client.post(
            "/books", json={"title": "Slaughterhouse-Five", "author": "Kurt Vonnegut"}
        )
        client.delete("/books/1")

        resp = client.get("/books")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []

    def test_delete_nonexistent_book_returns_404(self, client):
        """Scenario: Delete a book that does not exist

        Given no books exist
        When I DELETE /books/999
        Then I receive a 404 Not Found with an error message
        """
        resp = client.delete("/books/999")
        assert resp.status_code == 404
