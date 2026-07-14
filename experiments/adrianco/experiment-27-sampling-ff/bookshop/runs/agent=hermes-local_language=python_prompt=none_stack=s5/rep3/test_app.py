"""Comprehensive tests for the Book API REST Service."""

import pytest
import os
import sys

# Ensure the app module can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as book_app


@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database."""
    book_app.DATABASE = ':memory:'

    # Re-initialize the DB with in-memory storage
    book_app.init_db()

    book_app.app.config['TESTING'] = True

    with book_app.app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_db(client):
    """Reinitialize the database before each test to ensure isolation."""
    book_app.DATABASE = ':memory:'
    book_app.init_db()


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the health endpoint exists
        When I make a GET request to /health
        Then it should return status 200 with healthy status."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Tests for creating books (POST /books)."""

    def test_create_book_success(self, client):
        """Given a valid book payload
        When I POST to /books
        Then it should return 201 with the book data."""
        response = client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == 'The Great Gatsby'
        assert data['author'] == 'F. Scott Fitzgerald'
        assert data['year'] == 1925
        assert data['isbn'] == '978-0743273565'
        assert data['id'] is not None

    def test_create_book_missing_title(self, client):
        """Given a payload without title
        When I POST to /books
        Then it should return 400 with an error message."""
        response = client.post('/books', json={
            'author': 'Unknown Author',
            'year': 2000
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given a payload without author
        When I POST to /books
        Then it should return 400 with an error message."""
        response = client.post('/books', json={
            'title': 'Some Book'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_with_minimal_fields(self, client):
        """Given a payload with only title and author (required fields)
        When I POST to /books
        Then it should return 201 with null optional fields."""
        response = client.post('/books', json={
            'title': 'Minimal Book',
            'author': 'Author Name'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['year'] is None
        assert data['isbn'] is None

    def test_create_book_invalid_year(self, client):
        """Given a payload with non-integer year
        When I POST to /books
        Then it should return 400 with an error message."""
        response = client.post('/books', json={
            'title': 'Bad Year Book',
            'author': 'Author Name',
            'year': 'not a number'
        })
        assert response.status_code == 400


class TestListBooks:
    """Tests for listing books (GET /books)."""

    def test_list_books_empty(self, client):
        """Given no books in the database
        When I GET /books
        Then it should return an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_with_data(self, client):
        """Given some books in the database
        When I GET /books
        Then it should return all books."""
        # Create a book first
        client.post('/books', json={
            'title': 'Book One',
            'author': 'Author A',
            'year': 2020,
            'isbn': '111'
        })
        client.post('/books', json={
            'title': 'Book Two',
            'author': 'Author B',
            'year': 2021,
            'isbn': '222'
        })

        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given multiple books by different authors
        When I GET /books?author=Author%20A
        Then it should return only books by Author A."""
        client.post('/books', json={
            'title': 'Book One',
            'author': 'Author A',
            'year': 2020
        })
        client.post('/books', json={
            'title': 'Book Two',
            'author': 'Author B',
            'year': 2021
        })
        client.post('/books', json={
            'title': 'Book Three',
            'author': 'Author A Again',
            'year': 2022
        })

        response = client.get('/books?author=Author A')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2


class TestGetBook:
    """Tests for getting a single book (GET /books/<id>)."""

    def test_get_book_success(self, client):
        """Given a book exists in the database
        When I GET /books/1
        Then it should return the book data."""
        client.post('/books', json={
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '123-456'
        })

        response = client.get('/books/1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Test Book'

    def test_get_book_not_found(self, client):
        """Given no book with ID 999 exists
        When I GET /books/999
        Then it should return 404."""
        response = client.get('/books/999')
        assert response.status_code == 404


class TestUpdateBook:
    """Tests for updating a book (PUT /books/<id>)."""

    def test_update_book_success(self, client):
        """Given a book exists
        When I PUT to /books/1 with new data
        Then it should return the updated book."""
        # Create a book first
        client.post('/books', json={
            'title': 'Original Title',
            'author': 'Original Author',
            'year': 2020,
            'isbn': '111'
        })

        response = client.put('/books/1', json={
            'title': 'Updated Title',
            'author': 'Updated Author',
            'year': 2024,
            'isbn': '999'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Updated Title'
        assert data['author'] == 'Updated Author'
        assert data['year'] == 2024

    def test_update_book_not_found(self, client):
        """Given no book with ID 999 exists
        When I PUT to /books/999
        Then it should return 404."""
        response = client.put('/books/999', json={
            'title': 'Ghost Book'
        })
        assert response.status_code == 404

    def test_update_book_partial(self, client):
        """Given a book exists with full data
        When I PUT to /books/1 with only title updated
        Then it should return the book with only title changed."""
        client.post('/books', json={
            'title': 'Original Title',
            'author': 'Original Author',
            'year': 2020,
            'isbn': '111'
        })

        response = client.put('/books/1', json={
            'title': 'New Title Only'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'New Title Only'
        # Year and isbn should remain unchanged (stored as int, not None)
        assert data['year'] == 2020


class TestDeleteBook:
    """Tests for deleting a book (DELETE /books/<id>)."""

    def test_delete_book_success(self, client):
        """Given a book exists
        When I DELETE /books/1
        Then it should return 200 and the book should be gone."""
        # Create a book first
        client.post('/books', json={
            'title': 'ToDelete',
            'author': 'Author'
        })

        response = client.delete('/books/1')
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get('/books/1')
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given no book with ID 999 exists
        When I DELETE /books/999
        Then it should return 404."""
        response = client.delete('/books/999')
        assert response.status_code == 404


class TestIntegration:
    """Integration tests that exercise multiple endpoints together."""

    def test_full_crud_lifecycle(self, client):
        """Given an empty database
        When I create, read, update, and delete a book in sequence
        Then each step should succeed with correct status codes."""
        # CREATE
        create_resp = client.post('/books', json={
            'title': 'CRUD Test Book',
            'author': 'Integration Author',
            'year': 2025,
            'isbn': 'CRUD-ISBN'
        })
        assert create_resp.status_code == 201
        book_id = create_resp.get_json()['id']

        # READ (single)
        get_resp = client.get(f'/books/{book_id}')
        assert get_resp.status_code == 200
        assert get_resp.get_json()['title'] == 'CRUD Test Book'

        # READ (list)
        list_resp = client.get('/books')
        assert list_resp.status_code == 200
        assert len(list_resp.get_json()) == 1

        # UPDATE
        update_resp = client.put(f'/books/{book_id}', json={
            'title': 'Updated CRUD Book'
        })
        assert update_resp.status_code == 200

        # Verify update persisted
        get_resp = client.get(f'/books/{book_id}')
        assert get_resp.get_json()['title'] == 'Updated CRUD Book'

        # DELETE
        delete_resp = client.delete(f'/books/{book_id}')
        assert delete_resp.status_code == 200

        # Verify deletion
        get_resp = client.get(f'/books/{book_id}')
        assert get_resp.status_code == 404

    def test_create_multiple_books_and_filter(self, client):
        """Given multiple books by the same author
        When I filter by that author
        Then only their books should be returned."""
        # Create 3 books, 2 by Author X and 1 by Author Y
        client.post('/books', json={
            'title': 'Book 1',
            'author': 'Author X',
            'year': 2020
        })
        client.post('/books', json={
            'title': 'Book 2',
            'author': 'Author X',
            'year': 2021
        })
        client.post('/books', json={
            'title': 'Book 3',
            'author': 'Author Y',
            'year': 2022
        })

        # Filter by Author X
        response = client.get('/books?author=Author X')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert 'Author X' in book['author']

        # Filter by Author Y
        response = client.get('/books?author=Author Y')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
