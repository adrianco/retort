import pytest
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app


@pytest.fixture(autouse=True)
def client():
    """Create a test client with a fresh temp database for each test."""
    # Create a temp file for the test database
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()

    old_db = app.DATABASE
    app.DATABASE = tmp.name

    # Re-initialize the DB
    app.init_db()

    app.app.config['TESTING'] = True

    with app.app.test_client() as test_client:
        yield test_client

    # Restore original and clean up
    app.DATABASE = old_db
    os.unlink(tmp.name)


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_returns_200(self, client):
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test POST /books endpoint."""

    def test_create_book_success(self, client):
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
        response = client.post('/books',
                               data=json.dumps({
                                   'author': 'Test Author',
                                   'year': 2020
                               }),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        response = client.post('/books',
                               data=json.dumps({
                                   'title': 'Test Book',
                                   'year': 2020
                               }),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_empty_title(self, client):
        response = client.post('/books',
                               data=json.dumps({
                                   'title': '',
                                   'author': 'Test Author'
                               }),
                               content_type='application/json')
        assert response.status_code == 400

    def test_create_book_without_year_isbn(self, client):
        response = client.post('/books',
                               data=json.dumps({
                                   'title': 'Simple Book',
                                   'author': 'Author Name'
                               }),
                               content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['year'] is None
        assert data['isbn'] is None


class TestListBooks:
    """Test GET /books endpoint."""

    def test_list_books_empty(self, client):
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client):
        client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald',
            'year': 1925, 'isbn': '978-0743273565'
        }), content_type='application/json')
        client.post('/books', data=json.dumps({
            'title': '1984', 'author': 'George Orwell',
            'year': 1949, 'isbn': '978-0451524935'
        }), content_type='application/json')

        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        client.post('/books', data=json.dumps({
            'title': '1984', 'author': 'George Orwell',
            'year': 1949
        }), content_type='application/json')

        response = client.get('/books?author=George%20Orwell')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['author'] == 'George Orwell'


class TestGetBook:
    """Test GET /books/{id} endpoint."""

    def test_get_existing_book(self, client):
        response = client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        book_id = json.loads(response.data)['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby'

    def test_get_nonexistent_book(self, client):
        response = client.get('/books/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestUpdateBook:
    """Test PUT /books/{id} endpoint."""

    def test_update_book_success(self, client):
        response = client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        book_id = json.loads(response.data)['id']

        response = client.put(f'/books/{book_id}', data=json.dumps({
            'title': 'The Great Gatsby (Updated)',
            'author': 'F. Scott Fitzgerald'
        }), content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby (Updated)'
        assert data['author'] == 'F. Scott Fitzgerald'

    def test_update_nonexistent_book(self, client):
        response = client.put('/books/999', data=json.dumps({
            'title': 'New Title', 'author': 'New Author'
        }), content_type='application/json')
        assert response.status_code == 404


class TestDeleteBook:
    """Test DELETE /books/{id} endpoint."""

    def test_delete_book_success(self, client):
        response = client.post('/books', data=json.dumps({
            'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald',
            'year': 1925
        }), content_type='application/json')
        book_id = json.loads(response.data)['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify it's gone
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 404

    def test_delete_nonexistent_book(self, client):
        response = client.delete('/books/999')
        assert response.status_code == 404
