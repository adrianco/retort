import pytest
import os
import json
import sys

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    app_module.app.config['TESTING'] = True

    # Use a temporary database for testing
    original_db = app_module.DATABASE
    test_db_path = '/tmp/test_books.db'

    # Remove old test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    app_module.DATABASE = test_db_path
    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    # Clean up
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    app_module.DATABASE = original_db


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the API is running, when I hit the health endpoint,
        then I should get a 200 status with a healthy status."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test the POST /books endpoint."""

    def test_create_book_success(self, client):
        """Given a valid book request, when I POST to /books,
        then I should get a 201 response with the book data."""
        response = client.post('/books',
                              data=json.dumps({
                                  'title': 'The Great Gatsby',
                                  'author': 'F. Scott Fitzgerald',
                                  'year': 1925,
                                  'isbn': '978-0743273565'
                              }),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby'
        assert data['author'] == 'F. Scott Fitzgerald'
        assert data['year'] == 1925
        assert data['isbn'] == '978-0743273565'
        assert 'id' in data

    def test_create_book_missing_title(self, client):
        """Given a request without a title, when I POST to /books,
        then I should get a 400 error."""
        response = client.post('/books',
                              data=json.dumps({
                                  'author': 'F. Scott Fitzgerald',
                                  'year': 1925
                              }),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given a request without an author, when I POST to /books,
        then I should get a 400 error."""
        response = client.post('/books',
                              data=json.dumps({
                                  'title': 'The Great Gatsby',
                                  'year': 1925
                              }),
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_minimal_fields(self, client):
        """Given a request with only required fields, when I POST to /books,
        then I should get a 201 response."""
        response = client.post('/books',
                              data=json.dumps({
                                  'title': '1984',
                                  'author': 'George Orwell'
                              }),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == '1984'
        assert data['author'] == 'George Orwell'
        assert data['year'] is None
        assert data['isbn'] is None


class TestListBooks:
    """Test the GET /books endpoint."""

    def test_list_books_empty(self, client):
        """Given no books exist, when I GET /books,
        then I should get an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client):
        """Given some books exist, when I GET /books,
        then I should get a list of all books."""
        # Create some books first
        client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        client.post('/books', data=json.dumps({
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949
        }), content_type='application/json')

        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given books by multiple authors, when I GET /books?author=Orwell,
        then I should get only books by Orwell."""
        client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        client.post('/books', data=json.dumps({
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949
        }), content_type='application/json')
        client.post('/books', data=json.dumps({
            'title': 'Animal Farm',
            'author': 'George Orwell',
            'year': 1945
        }), content_type='application/json')

        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        for book in data:
            assert 'orwell' in book['author'].lower()

    def test_list_books_filter_by_author_no_match(self, client):
        """Given books by known authors, when I GET /books?author=Unknown,
        then I should get an empty list."""
        client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')

        response = client.get('/books?author=Unknown')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []


class TestGetBook:
    """Test the GET /books/<id> endpoint."""

    def test_get_book_existing(self, client):
        """Given a book exists, when I GET /books/{id},
        then I should get the book data."""
        response = client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }), content_type='application/json')
        book_data = json.loads(response.data)
        book_id = book_data['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby'
        assert data['author'] == 'F. Scott Fitzgerald'

    def test_get_book_not_found(self, client):
        """Given a book doesn't exist, when I GET /books/{id},
        then I should get a 404 error."""
        response = client.get('/books/9999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestUpdateBook:
    """Test the PUT /books/<id> endpoint."""

    def test_update_book_success(self, client):
        """Given a book exists, when I PUT /books/{id},
        then I should get the updated book data."""
        response = client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        book_data = json.loads(response.data)
        book_id = book_data['id']

        response = client.put(f'/books/{book_id}', data=json.dumps({
            'title': 'The Great Gatsby (Updated)',
            'year': 1926
        }), content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby (Updated)'
        assert data['author'] == 'F. Scott Fitzgerald'  # unchanged
        assert data['year'] == 1926

    def test_update_book_not_found(self, client):
        """Given a book doesn't exist, when I PUT /books/{id},
        then I should get a 404 error."""
        response = client.put('/books/9999', data=json.dumps({
            'title': 'Nonexistent'
        }), content_type='application/json')
        assert response.status_code == 404

    def test_update_book_empty_title(self, client):
        """Given a book exists, when I PUT with empty title,
        then I should get a 400 error."""
        response = client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald'
        }), content_type='application/json')
        book_data = json.loads(response.data)
        book_id = book_data['id']

        response = client.put(f'/books/{book_id}', data=json.dumps({
            'title': ''
        }), content_type='application/json')
        assert response.status_code == 400


class TestDeleteBook:
    """Test the DELETE /books/<id> endpoint."""

    def test_delete_book_success(self, client):
        """Given a book exists, when I DELETE /books/{id},
        then I should get a success message and the book should be gone."""
        response = client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        book_data = json.loads(response.data)
        book_id = book_data['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify the book is gone
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a book doesn't exist, when I DELETE /books/{id},
        then I should get a 404 error."""
        response = client.delete('/books/9999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
