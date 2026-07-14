import pytest
import os
import sys
import tempfile

# Ensure the app module can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    app_module.app.config['TESTING'] = True
    # Use a temp database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    original_db = app_module.DATABASE
    app_module.DATABASE = db_path

    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    app_module.DATABASE = original_db
    os.unlink(db_path)


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_returns_200(self, client):
        """Given the health endpoint exists, when called, then it returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test creating books via POST /books."""

    def test_create_book_success(self, client):
        """Given valid book data, when POST /books is called, then a book is created with 201."""
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
        """Given missing title, when POST /books is called, then it returns 400."""
        response = client.post('/books', json={
            'author': 'Unknown Author',
            'year': 2000
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given missing author, when POST /books is called, then it returns 400."""
        response = client.post('/books', json={
            'title': 'Some Book',
            'year': 2000
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_no_json_body(self, client):
        """Given no JSON body, when POST /books is called, then it returns 400."""
        response = client.post('/books', content_type='application/json')
        assert response.status_code == 400


class TestListBooks:
    """Test listing books via GET /books."""

    def test_list_books_empty(self, client):
        """Given no books exist, when GET /books is called, then it returns empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_with_data(self, client):
        """Given books exist, when GET /books is called, then it returns all books."""
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
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given books by multiple authors, when GET /books?author=Orwell is called, then only Orwell books are returned."""
        client.post('/books', json={
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949
        })
        client.post('/books', json={
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        })
        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['author'] == 'George Orwell'


class TestGetBook:
    """Test getting a single book via GET /books/{id}."""

    def test_get_book_success(self, client):
        """Given a book exists, when GET /books/{id} is called, then it returns the book."""
        response = client.post('/books', json={
            'title': 'Dune',
            'author': 'Frank Herbert',
            'year': 1965
        })
        book_id = response.get_json()['id']
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Dune'

    def test_get_book_not_found(self, client):
        """Given a book does not exist, when GET /books/999 is called, then it returns 404."""
        response = client.get('/books/999')
        assert response.status_code == 404


class TestUpdateBook:
    """Test updating a book via PUT /books/{id}."""

    def test_update_book_success(self, client):
        """Given a book exists, when PUT /books/{id} is called, then it returns the updated book."""
        response = client.post('/books', json={
            'title': 'Old Title',
            'author': 'Old Author',
            'year': 2000
        })
        book_id = response.get_json()['id']
        response = client.put(f'/books/{book_id}', json={
            'title': 'New Title',
            'author': 'New Author',
            'year': 2020
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'New Title'
        assert data['author'] == 'New Author'
        assert data['year'] == 2020

    def test_update_book_not_found(self, client):
        """Given a book does not exist, when PUT /books/999 is called, then it returns 404."""
        response = client.put('/books/999', json={
            'title': 'New Title',
            'author': 'New Author'
        })
        assert response.status_code == 404

    def test_update_book_missing_title(self, client):
        """Given a book exists, when PUT /books/{id} with missing title, then it returns 400."""
        response = client.post('/books', json={
            'title': 'Old Title',
            'author': 'Old Author'
        })
        book_id = response.get_json()['id']
        response = client.put(f'/books/{book_id}', json={
            'author': 'New Author'
        })
        assert response.status_code == 400


class TestDeleteBook:
    """Test deleting a book via DELETE /books/{id}."""

    def test_delete_book_success(self, client):
        """Given a book exists, when DELETE /books/{id} is called, then it returns 200 and the book is gone."""
        response = client.post('/books', json={
            'title': 'To Delete',
            'author': 'Someone',
            'year': 2020
        })
        book_id = response.get_json()['id']
        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

        # Verify the book is actually deleted
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a book does not exist, when DELETE /books/999 is called, then it returns 404."""
        response = client.delete('/books/999')
        assert response.status_code == 404
