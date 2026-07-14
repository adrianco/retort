"""Acceptance tests for the Book API REST Service."""

import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture(autouse=True)
def setup_db():
    """Set up a temporary file-based database for each test."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    original_db = app_module.DATABASE
    app_module.DATABASE = tmp.name
    app_module.init_db()
    yield
    app_module.DATABASE = original_db
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest.fixture
def client(setup_db):
    """Create a test client with a fresh temporary database."""
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_returns_200(self, client):
        """Given the health endpoint exists, when called, then returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test creating books via POST /books."""

    def test_create_book_success(self, client):
        """Given valid book data, when POST /books, then returns 201 with book."""
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
        assert 'id' in data

    def test_create_book_missing_title(self, client):
        """Given missing title, when POST /books, then returns 400."""
        response = client.post('/books', json={
            'author': 'Unknown Author',
            'year': 2000
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given missing author, when POST /books, then returns 400."""
        response = client.post('/books', json={
            'title': 'Some Book',
            'year': 2000
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_invalid_year(self, client):
        """Given invalid year, when POST /books, then returns 400."""
        response = client.post('/books', json={
            'title': 'Some Book',
            'author': 'Some Author',
            'year': 'not-a-year'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestListBooks:
    """Test listing books via GET /books."""

    def test_list_books_empty(self, client):
        """Given no books, when GET /books, then returns empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_with_data(self, client):
        """Given books exist, when GET /books, then returns all books."""
        client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        client.post('/books', json={
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949
        })

        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given books by multiple authors, when GET /books?author=Orwell, then returns only Orwell books."""
        client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        client.post('/books', json={
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949
        })
        client.post('/books', json={
            'title': 'Animal Farm',
            'author': 'George Orwell',
            'year': 1945
        })

        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert 'Orwell' in book['author']


class TestGetBook:
    """Test getting a single book via GET /books/{id}."""

    def test_get_book_success(self, client):
        """Given a book exists, when GET /books/{id}, then returns the book."""
        response = client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        book_id = response.get_json()['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'The Great Gatsby'

    def test_get_book_not_found(self, client):
        """Given a book does not exist, when GET /books/{id}, then returns 404."""
        response = client.get('/books/999')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data


class TestUpdateBook:
    """Test updating a book via PUT /books/{id}."""

    def test_update_book_success(self, client):
        """Given a book exists, when PUT /books/{id}, then returns updated book."""
        response = client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        book_id = response.get_json()['id']

        response = client.put(f'/books/{book_id}', json={
            'title': 'The Great Gatsby (Updated)',
            'author': 'F. Scott Fitzgerald'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'The Great Gatsby (Updated)'
        assert data['author'] == 'F. Scott Fitzgerald'

    def test_update_book_not_found(self, client):
        """Given a book does not exist, when PUT /books/{id}, then returns 404."""
        response = client.put('/books/999', json={
            'title': 'Nonexistent',
            'author': 'Nobody'
        })
        assert response.status_code == 404

    def test_update_book_missing_title(self, client):
        """Given a book exists, when PUT with empty title, then returns 400."""
        response = client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        book_id = response.get_json()['id']

        response = client.put(f'/books/{book_id}', json={
            'title': '',
            'author': 'F. Scott Fitzgerald'
        })
        assert response.status_code == 400


class TestDeleteBook:
    """Test deleting a book via DELETE /books/{id}."""

    def test_delete_book_success(self, client):
        """Given a book exists, when DELETE /books/{id}, then returns 200 and book is gone."""
        response = client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        book_id = response.get_json()['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

        # Verify book is gone
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a book does not exist, when DELETE /books/{id}, then returns 404."""
        response = client.delete('/books/999')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data


class TestIntegration:
    """Integration tests covering full workflows."""

    def test_full_crud_lifecycle(self, client):
        """Given an empty collection, when performing full CRUD, then data is consistent."""
        # CREATE
        response = client.post('/books', json={
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949,
            'isbn': '978-0451524935'
        })
        assert response.status_code == 201
        book_id = response.get_json()['id']

        # READ
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        assert response.get_json()['title'] == '1984'

        # UPDATE
        response = client.put(f'/books/{book_id}', json={
            'title': '1984 (Special Edition)',
            'author': 'George Orwell',
            'year': 1949,
            'isbn': '978-0451524935'
        })
        assert response.status_code == 200
        assert response.get_json()['title'] == '1984 (Special Edition)'

        # DELETE
        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200

        # Verify deletion
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 404

    def test_list_with_filter_and_pagination(self, client):
        """Given multiple books, when filtering by author, then only matching books returned."""
        client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        client.post('/books', json={
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949
        })
        client.post('/books', json={
            'title': 'Brave New World',
            'author': 'Aldous Huxley',
            'year': 1932
        })

        response = client.get('/books?author=Fitzgerald')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['title'] == 'The Great Gatsby'
