import pytest
import os
import json
import tempfile
from app import create_app, init_db


@pytest.fixture
def client():
    """Create a test client with a temporary in-memory database."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    test_config = {
        'DATABASE': db_path,
        'TESTING': True,
    }

    app = create_app(test_config)

    # Initialize the database with explicit path
    init_db(db_path)

    with app.test_client() as test_client:
        yield test_client

    os.unlink(db_path)


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given no state, When health is checked, Then it returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test creating books."""

    def test_create_book_success(self, client):
        """Given valid book data, When created, Then it returns 201 with book."""
        response = client.post('/books',
                               data=json.dumps({
                                   'title': '1984',
                                   'author': 'George Orwell',
                                   'year': 1949,
                                   'isbn': '978-0451524935'
                               }),
                               content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == '1984'
        assert data['author'] == 'George Orwell'
        assert data['year'] == 1949
        assert data['isbn'] == '978-0451524935'
        assert 'id' in data

    def test_create_book_missing_title(self, client):
        """Given missing title, When created, Then it returns 400."""
        response = client.post('/books',
                               data=json.dumps({
                                   'author': 'George Orwell',
                                   'year': 1949
                               }),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given missing author, When created, Then it returns 400."""
        response = client.post('/books',
                               data=json.dumps({
                                   'title': '1984',
                                   'year': 1949
                               }),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_no_body(self, client):
        """Given no body, When created, Then it returns 400."""
        response = client.post('/books',
                               content_type='application/json')
        assert response.status_code == 400


class TestListBooks:
    """Test listing books."""

    def test_list_books_empty(self, client):
        """Given no books, When listed, Then it returns empty array."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_after_create(self, client):
        """Given books exist, When listed, Then it returns all books."""
        # Create a book first
        client.post('/books',
                    data=json.dumps({
                        'title': '1984',
                        'author': 'George Orwell',
                        'year': 1949
                    }),
                    content_type='application/json')
        client.post('/books',
                    data=json.dumps({
                        'title': 'Animal Farm',
                        'author': 'George Orwell',
                        'year': 1945
                    }),
                    content_type='application/json')

        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given books by multiple authors, When filtered by author, Then only matching books returned."""
        client.post('/books',
                    data=json.dumps({
                        'title': '1984',
                        'author': 'George Orwell',
                        'year': 1949
                    }),
                    content_type='application/json')
        client.post('/books',
                    data=json.dumps({
                        'title': 'The Great Gatsby',
                        'author': 'F. Scott Fitzgerald',
                        'year': 1925
                    }),
                    content_type='application/json')

        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['author'] == 'George Orwell'


class TestGetBook:
    """Test getting a single book."""

    def test_get_book_not_found(self, client):
        """Given nonexistent ID, When fetched, Then it returns 404."""
        response = client.get('/books/9999')
        assert response.status_code == 404

    def test_get_book_success(self, client):
        """Given existing book, When fetched, Then it returns the book."""
        # Create a book first
        client.post('/books',
                    data=json.dumps({
                        'title': '1984',
                        'author': 'George Orwell',
                        'year': 1949
                    }),
                    content_type='application/json')

        response = client.get('/books/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == '1984'


class TestUpdateBook:
    """Test updating books."""

    def test_update_book_not_found(self, client):
        """Given nonexistent ID, When updated, Then it returns 404."""
        response = client.put('/books/9999',
                              data=json.dumps({'title': 'New Title'}),
                              content_type='application/json')
        assert response.status_code == 404

    def test_update_book_success(self, client):
        """Given existing book, When updated, Then it returns updated book."""
        # Create a book first
        client.post('/books',
                    data=json.dumps({
                        'title': '1984',
                        'author': 'George Orwell',
                        'year': 1949
                    }),
                    content_type='application/json')

        response = client.put('/books/1',
                              data=json.dumps({
                                  'title': 'Nineteen Eighty-Four',
                                  'year': 1949
                              }),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Nineteen Eighty-Four'
        assert data['author'] == 'George Orwell'  # unchanged


class TestDeleteBook:
    """Test deleting books."""

    def test_delete_book_not_found(self, client):
        """Given nonexistent ID, When deleted, Then it returns 404."""
        response = client.delete('/books/9999')
        assert response.status_code == 404

    def test_delete_book_success(self, client):
        """Given existing book, When deleted, Then it returns success and book is gone."""
        # Create a book first
        client.post('/books',
                    data=json.dumps({
                        'title': '1984',
                        'author': 'George Orwell',
                        'year': 1949
                    }),
                    content_type='application/json')

        response = client.delete('/books/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify it's gone
        response = client.get('/books/1')
        assert response.status_code == 404
