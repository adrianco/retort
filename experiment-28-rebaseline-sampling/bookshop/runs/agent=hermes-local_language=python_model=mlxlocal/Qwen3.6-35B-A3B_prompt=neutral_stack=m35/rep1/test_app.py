"""Tests for the Book Collection REST API."""

import json
import os
import sys
import tempfile
import pytest

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    # Use a temporary database file for testing
    db_path = tempfile.mktemp(suffix='.db')
    app_module.DATABASE = db_path
    app_module.init_db()

    test_client = app_module.app.test_client()

    yield test_client

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def sample_books(client):
    """Pre-populate the database with sample books."""
    books_data = [
        {'title': '1984', 'author': 'George Orwell', 'year': 1949, 'isbn': '978-0451524935'},
        {'title': 'Animal Farm', 'author': 'George Orwell', 'year': 1945, 'isbn': '978-0451526342'},
        {'title': 'Brave New World', 'author': 'Aldous Huxley', 'year': 1932, 'isbn': '978-0060850524'},
    ]
    created = []
    for book_data in books_data:
        resp = client.post('/books', json=book_data)
        assert resp.status_code == 201
        created.append(json.loads(resp.data))
    return created


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the health endpoint exists, when called, then returns 200 with healthy status."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test the POST /books endpoint."""

    def test_create_book_success(self, client):
        """Given valid book data, when creating a book, then returns 201 with the book."""
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby'
        assert data['author'] == 'F. Scott Fitzgerald'
        assert data['year'] == 1925
        assert data['isbn'] == '978-0743273565'
        assert 'id' in data

    def test_create_book_missing_title(self, client):
        """Given missing title, when creating a book, then returns 400 with error."""
        book_data = {'author': 'Test Author', 'year': 2020}
        response = client.post('/books', json=book_data)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given missing author, when creating a book, then returns 400 with error."""
        book_data = {'title': 'Test Book', 'year': 2020}
        response = client.post('/books', json=book_data)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_no_body(self, client):
        """Given no request body, when creating a book, then returns 400."""
        response = client.post('/books', content_type='application/json', data='')
        assert response.status_code == 400


class TestListBooks:
    """Test the GET /books endpoint."""

    def test_list_books_empty(self, client):
        """Given no books, when listing, then returns empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client, sample_books):
        """Given books exist, when listing, then returns all books."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client, sample_books):
        """Given books by multiple authors, when filtering by author, then returns matching books."""
        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        for book in data:
            assert 'orwell' in book['author'].lower()

    def test_list_books_filter_no_match(self, client, sample_books):
        """Given books, when filtering by non-existent author, then returns empty list."""
        response = client.get('/books?author=NonExistent')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 0


class TestGetBook:
    """Test the GET /books/{id} endpoint."""

    def test_get_book_success(self, client, sample_books):
        """Given a book exists, when getting by id, then returns the book."""
        book_id = sample_books[0]['id']
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == book_id
        assert data['title'] == '1984'

    def test_get_book_not_found(self, client):
        """Given no book with that id, when getting by id, then returns 404."""
        response = client.get('/books/9999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestUpdateBook:
    """Test the PUT /books/{id} endpoint."""

    def test_update_book_success(self, client, sample_books):
        """Given a book exists, when updating, then returns the updated book."""
        book_id = sample_books[0]['id']
        update_data = {
            'title': '1984 (Updated Edition)',
            'author': 'George Orwell',
            'year': 1949,
            'isbn': '978-0451524935'
        }
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == '1984 (Updated Edition)'
        assert data['id'] == book_id

    def test_update_book_partial(self, client, sample_books):
        """Given a book exists, when updating only some fields, then returns updated book."""
        book_id = sample_books[0]['id']
        update_data = {'title': '1984 (Special Edition)'}
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == '1984 (Special Edition)'
        assert data['author'] == 'George Orwell'  # unchanged

    def test_update_book_not_found(self, client):
        """Given non-existent book, when updating, then returns 404."""
        response = client.put('/books/9999', json={'title': 'Test'})
        assert response.status_code == 404

    def test_update_book_missing_title_keeps_existing(self, client, sample_books):
        """Given a book exists, when updating without title, then keeps existing title."""
        book_id = sample_books[0]['id']
        update_data = {'author': 'New Author'}
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == '1984'  # existing title preserved
        assert data['author'] == 'New Author'


class TestDeleteBook:
    """Test the DELETE /books/{id} endpoint."""

    def test_delete_book_success(self, client, sample_books):
        """Given a book exists, when deleting, then returns 200 and book is gone."""
        book_id = sample_books[0]['id']
        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify the book is gone
        get_response = client.get(f'/books/{book_id}')
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given non-existent book, when deleting, then returns 404."""
        response = client.delete('/books/9999')
        assert response.status_code == 404

    def test_delete_book_removes_from_list(self, client, sample_books):
        """Given multiple books, when deleting one, then list has one fewer."""
        book_id = sample_books[0]['id']
        client.delete(f'/books/{book_id}')
        response = client.get('/books')
        data = json.loads(response.data)
        assert len(data) == 2
