"""
Acceptance tests for the Book API REST Service.

These tests are written from the perspective of an external client
exercising only the public REST API (HTTP endpoints, JSON contracts,
status codes). Each scenario is atomic and independent -- every test
starts from a running but empty service and shares no data with other tests.
"""
import json
import pytest
import requests

BASE_URL = "http://127.0.0.1:5001"


# -- Health Check --

class TestHealthCheck:
    """Acceptance tests for the health check endpoint."""

    def test_health_check_returns_200(self):
        """Given the service is running,
        When I GET /health,
        Then I receive a 200 OK response with a JSON body indicating health."""
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert body["status"] == "ok"

    def test_health_check_content_type_is_json(self):
        """Given the service is running,
        When I GET /health,
        Then the response Content-Type header is application/json."""
        resp = requests.get(f"{BASE_URL}/health")
        assert "application/json" in resp.headers.get("Content-Type", "")


# -- Create Book -- POST /books

class TestCreateBook:
    """Acceptance tests for creating a new book."""

    def test_create_book_successfully_returns_201(self):
        """Given an empty book collection,
        When I POST /books with title, author, year, and isbn,
        Then I receive a 201 Created response with the created book in JSON."""
        payload = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }
        resp = requests.post(f"{BASE_URL}/books", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["title"] == "The Great Gatsby"
        assert body["author"] == "F. Scott Fitzgerald"
        assert body["year"] == 1925
        assert body["isbn"] == "978-0743273565"

    def test_create_book_auto_assigns_integer_id(self):
        """Given an empty book collection,
        When I POST /books with a new book,
        Then the response includes an auto-assigned positive integer id."""
        payload = {
            "title": "1984",
            "author": "George Orwell",
            "year": 1949,
            "isbn": "978-0451524935"
        }
        resp = requests.post(f"{BASE_URL}/books", json=payload)
        assert resp.status_code == 201
        assert isinstance(resp.json()["id"], int)
        assert resp.json()["id"] > 0

    def test_create_book_requires_title(self):
        """Given an empty book collection,
        When I POST /books with a missing title,
        Then I receive a 400 Bad Request error."""
        payload = {
            "author": "Anonymous",
            "year": 2020,
            "isbn": "000-0000000000"
        }
        resp = requests.post(f"{BASE_URL}/books", json=payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body

    def test_create_book_requires_author(self):
        """Given an empty book collection,
        When I POST /books with a missing author,
        Then I receive a 400 Bad Request error."""
        payload = {
            "title": "Untitled",
            "year": 2020,
            "isbn": "000-0000000000"
        }
        resp = requests.post(f"{BASE_URL}/books", json=payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body

    def test_create_book_requires_non_empty_title(self):
        """Given an empty book collection,
        When I POST /books with an empty title,
        Then I receive a 400 Bad Request error."""
        payload = {
            "title": "",
            "author": "Someone",
            "year": 2020,
            "isbn": "000-0000000000"
        }
        resp = requests.post(f"{BASE_URL}/books", json=payload)
        assert resp.status_code == 400

    def test_create_book_requires_non_empty_author(self):
        """Given an empty book collection,
        When I POST /books with an empty author,
        Then I receive a 400 Bad Request error."""
        payload = {
            "title": "Some Title",
            "author": "",
            "year": 2020,
            "isbn": "000-0000000000"
        }
        resp = requests.post(f"{BASE_URL}/books", json=payload)
        assert resp.status_code == 400

    def test_create_book_with_year_and_isbn_optional(self):
        """Given an empty book collection,
        When I POST /books with only title and author,
        Then the book is created successfully with 201."""
        payload = {
            "title": "Simple Book",
            "author": "Simple Author"
        }
        resp = requests.post(f"{BASE_URL}/books", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Simple Book"
        assert body["author"] == "Simple Author"
        assert body["year"] is None
        assert body["isbn"] is None


# -- List All Books -- GET /books

class TestListBooks:
    """Acceptance tests for listing books."""

    def test_list_empty_collection_returns_200_with_empty_list(self):
        """Given an empty book collection,
        When I GET /books,
        Then I receive a 200 OK response with an empty JSON array."""
        resp = requests.get(f"{BASE_URL}/books")
        assert resp.status_code == 200
        body = resp.json()
        assert body == []

    def test_list_books_returns_all_created_books(self):
        """Given the collection contains 3 books,
        When I GET /books,
        Then I receive all 3 books in the response."""
        for data in [
            {"title": "Book One", "author": "Author A", "year": 2000, "isbn": "001"},
            {"title": "Book Two", "author": "Author B", "year": 2001, "isbn": "002"},
            {"title": "Book Three", "author": "Author C", "year": 2002, "isbn": "003"},
        ]:
            requests.post(f"{BASE_URL}/books", json=data)

        resp = requests.get(f"{BASE_URL}/books")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3

    def test_list_books_sorted_by_id(self):
        """Given the collection contains multiple books,
        When I GET /books,
        Then the books are returned in ascending id order."""
        requests.post(f"{BASE_URL}/books", json={
            "title": "Later Book", "author": "Author Z", "year": 2010, "isbn": "zzz"})
        requests.post(f"{BASE_URL}/books", json={
            "title": "First Book", "author": "Author A", "year": 1990, "isbn": "aaa"})

        resp = requests.get(f"{BASE_URL}/books")
        assert resp.status_code == 200
        body = resp.json()
        ids = [b["id"] for b in body]
        assert ids == sorted(ids)


# -- Filter Books by Author -- GET /books?author=

class TestFilterBooksByAuthor:
    """Acceptance tests for filtering books by author."""

    def test_filter_by_author_returns_matching_books(self):
        """Given the collection contains books from multiple authors,
        When I GET /books?author=J.K. Rowling,
        Then I receive only the books written by J.K. Rowling."""
        requests.post(f"{BASE_URL}/books", json={
            "title": "Harry Potter", "author": "J.K. Rowling", "year": 1997, "isbn": "hp"})
        requests.post(f"{BASE_URL}/books", json={
            "title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "ho"})
        requests.post(f"{BASE_URL}/books", json={
            "title": "Another Rowling", "author": "J.K. Rowling", "year": 2001, "isbn": "cs"})

        resp = requests.get(f"{BASE_URL}/books", params={"author": "J.K. Rowling"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        for book in body:
            assert book["author"] == "J.K. Rowling"

    def test_filter_by_author_returns_empty_when_no_match(self):
        """Given the collection contains books but none by a given author,
        When I GET /books?author=Nobody,
        Then I receive an empty JSON array."""
        requests.post(f"{BASE_URL}/books", json={
            "title": "Some Book", "author": "Some Author", "year": 2020, "isbn": "sa"})

        resp = requests.get(f"{BASE_URL}/books", params={"author": "Nobody"})
        assert resp.status_code == 200
        body = resp.json()
        assert body == []


# -- Get Single Book -- GET /books/{id}

class TestGetSingleBook:
    """Acceptance tests for retrieving a single book by ID."""

    def test_get_existing_book_returns_200_with_book(self):
        """Given a book exists in the collection,
        When I GET /books/{id} for that book,
        Then I receive a 200 OK response with the book in JSON."""
        resp = requests.post(f"{BASE_URL}/books", json={
            "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "dune"})
        book_id = resp.json()["id"]

        resp = requests.get(f"{BASE_URL}/books/{book_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Dune"
        assert body["author"] == "Frank Herbert"

    def test_get_nonexistent_book_returns_404(self):
        """Given no book exists with the given ID,
        When I GET /books/99999,
        Then I receive a 404 Not Found response."""
        resp = requests.get(f"{BASE_URL}/books/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body

    def test_get_book_by_id_201_created(self):
        """Given a book was just created,
        When I GET /books/{id} for that book,
        Then I can retrieve it and it matches what was created."""
        payload = {
            "title": "Brave New World",
            "author": "Aldous Huxley",
            "year": 1932,
            "isbn": "bnw"
        }
        create_resp = requests.post(f"{BASE_URL}/books", json=payload)
        book_id = create_resp.json()["id"]

        get_resp = requests.get(f"{BASE_URL}/books/{book_id}")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["title"] == payload["title"]
        assert body["author"] == payload["author"]
        assert body["year"] == payload["year"]
        assert body["isbn"] == payload["isbn"]


# -- Update Book -- PUT /books/{id}

class TestUpdateBook:
    """Acceptance tests for updating a book."""

    def test_update_existing_book_returns_200_with_updated_book(self):
        """Given a book exists,
        When I PUT /books/{id} with updated data,
        Then I receive a 200 OK response with the updated book."""
        create_resp = requests.post(f"{BASE_URL}/books", json={
            "title": "Old Title", "author": "Old Author", "year": 1900, "isbn": "old"})
        book_id = create_resp.json()["id"]

        resp = requests.put(f"{BASE_URL}/books/{book_id}", json={
            "title": "New Title", "author": "New Author", "year": 2020, "isbn": "new"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "New Title"
        assert body["author"] == "New Author"
        assert body["year"] == 2020
        assert body["isbn"] == "new"

    def test_update_nonexistent_book_returns_404(self):
        """Given no book exists with the given ID,
        When I PUT /books/99999 with updated data,
        Then I receive a 404 Not Found response."""
        resp = requests.put(f"{BASE_URL}/books/99999", json={
            "title": "Gone Title", "author": "Gone Author"})
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body

    def test_update_rejects_missing_title(self):
        """Given a book exists,
        When I PUT /books/{id} with an empty title,
        Then I receive a 400 Bad Request error."""
        create_resp = requests.post(f"{BASE_URL}/books", json={
            "title": "Keep Title", "author": "Keep Author", "year": 2000, "isbn": "keep"})
        book_id = create_resp.json()["id"]

        resp = requests.put(f"{BASE_URL}/books/{book_id}", json={
            "title": "", "author": "Keep Author"})
        assert resp.status_code == 400

    def test_update_rejects_missing_author(self):
        """Given a book exists,
        When I PUT /books/{id} with an empty author,
        Then I receive a 400 Bad Request error."""
        create_resp = requests.post(f"{BASE_URL}/books", json={
            "title": "Keep Title", "author": "Keep Author", "year": 2000, "isbn": "keep"})
        book_id = create_resp.json()["id"]

        resp = requests.put(f"{BASE_URL}/books/{book_id}", json={
            "title": "Keep Title", "author": ""})
        assert resp.status_code == 400

    def test_partial_update_updates_only_specified_fields(self):
        """Given a book exists with full data,
        When I PUT /books/{id} with only some fields,
        Then only those fields are changed and others are preserved."""
        create_resp = requests.post(f"{BASE_URL}/books", json={
            "title": "Original Title", "author": "Original Author", "year": 1990, "isbn": "orig"})
        book_id = create_resp.json()["id"]

        resp = requests.put(f"{BASE_URL}/books/{book_id}", json={
            "title": "Updated Title"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Updated Title"
        assert body["author"] == "Original Author"
        assert body["year"] == 1990
        assert body["isbn"] == "orig"


# -- Delete Book -- DELETE /books/{id}

class TestDeleteBook:
    """Acceptance tests for deleting a book."""

    def test_delete_existing_book_returns_200(self):
        """Given a book exists,
        When I DELETE /books/{id},
        Then I receive a 200 OK response with a confirmation message."""
        create_resp = requests.post(f"{BASE_URL}/books", json={
            "title": "Gone Book", "author": "Gone Author", "year": 2020, "isbn": "gone"})
        book_id = create_resp.json()["id"]

        resp = requests.delete(f"{BASE_URL}/books/{book_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body

    def test_delete_existing_book_removes_it_from_collection(self):
        """Given a book exists,
        When I DELETE /books/{id},
        Then GET /books no longer returns that book."""
        create_resp = requests.post(f"{BASE_URL}/books", json={
            "title": "Deleted Book", "author": "Deleted Author", "year": 2020, "isbn": "del"})
        book_id = create_resp.json()["id"]

        requests.delete(f"{BASE_URL}/books/{book_id}")

        resp = requests.get(f"{BASE_URL}/books")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 0

    def test_delete_nonexistent_book_returns_404(self):
        """Given no book exists with the given ID,
        When I DELETE /books/99999,
        Then I receive a 404 Not Found response."""
        resp = requests.delete(f"{BASE_URL}/books/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
