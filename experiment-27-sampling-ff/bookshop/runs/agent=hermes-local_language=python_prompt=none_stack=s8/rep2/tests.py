"""Tests for the Book Collection REST API."""

import os
import json
import pytest
import sys

# Ensure the app module is importable from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as book_app


@pytest.fixture
def client():
    """Create a test client with a fresh database."""
    book_app.app.config['TESTING'] = True

    # Use an in-memory database for tests
    db_path = os.path.join(os.path.dirname(book_app.DATABASE), 'test_books.db')
    book_app.app.config['DATABASE_PATH'] = db_path

    # Override the DATABASE path
    old_db = book_app.DATABASE
    book_app.DATABASE = db_path

    # Reinitialize the test database
    book_app.init_db()

    with book_app.app.test_client() as client:
        yield client

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Tests for creating books."""

    def test_create_book_success(self, client):
        response = client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby'
        assert data['author'] == 'F. Scott Fitzgerald'
        assert data['year'] == 1925
        assert data['isbn'] == '978-0743273565'
        assert data['id'] is not None

    def test_create_book_missing_title(self, client):
        response = client.post('/books', json={
            'author': 'F. Scott Fitzgerald'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        response = client.post('/books', json={
            'title': 'The Great Gatsby'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_duplicate_isbn(self, client):
        # Create first book
        client.post('/books', json={
            'title': 'Book One',
            'author': 'Author One',
            'year': 2020,
            'isbn': '123-ABC'
        })
        # Try to create book with same ISBN
        response = client.post('/books', json={
            'title': 'Book Two',
            'author': 'Author Two',
            'year': 2021,
            'isbn': '123-ABC'
        })
        assert response.status_code == 409


class TestListBooks:
    """Tests for listing books."""

    def test_list_books_empty(self, client):
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client):
        # Create some books
        for i in range(3):
            client.post('/books', json={
                'title': f'Book {i}',
                'author': 'Author A',
                'year': 2020 + i,
            })

        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client):
        # Create books with different authors
        client.post('/books', json={
            'title': 'Book One',
            'author': 'Alice Smith',
        })
        client.post('/books', json={
            'title': 'Book Two',
            'author': 'Bob Jones',
        })
        client.post('/books', json={
            'title': 'Book Three',
            'author': 'Alice Brown',
        })

        response = client.get('/books?author=Alice')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2


class TestGetBook:
    """Tests for getting a single book."""

    def test_get_book_not_found(self, client):
        response = client.get('/books/999')
        assert response.status_code == 404

    def test_get_book_success(self, client):
        # Create a book first
        create_resp = client.post('/books', json={
            'title': 'Test Book',
            'author': 'Test Author',
        })
        book_id = json.loads(create_resp.data)['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Test Book'


class TestUpdateBook:
    """Tests for updating a book."""

    def test_update_book_success(self, client):
        # Create a book first
        create_resp = client.post('/books', json={
            'title': 'Original Title',
            'author': 'Original Author',
        })
        book_id = json.loads(create_resp.data)['id']

        response = client.put(f'/books/{book_id}', json={
            'title': 'Updated Title',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Updated Title'
        assert data['author'] == 'Original Author'

    def test_update_book_not_found(self, client):
        response = client.put('/books/999', json={
            'title': 'Updated Title'
        })
        assert response.status_code == 404


class TestDeleteBook:
    """Tests for deleting a book."""

    def test_delete_book_success(self, client):
        # Create a book first
        create_resp = client.post('/books', json={
            'title': 'To Delete',
            'author': 'Author',
        })
        book_id = json.loads(create_resp.data)['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200

        # Verify it's gone
        get_resp = client.get(f'/books/{book_id}')
        assert get_resp.status_code == 404

    def test_delete_book_not_found(self, client):
        response = client.delete('/books/999')
        assert response.status_code == 404
