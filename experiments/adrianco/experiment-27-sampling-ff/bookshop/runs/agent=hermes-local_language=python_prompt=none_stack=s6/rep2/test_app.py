import os
import json
import tempfile
import pytest

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    app_module.app.config['TESTING'] = True

    # Use a temporary database for tests
    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp_db.close()
    app_module.app.config['DATABASE'] = tmp_db.name

    # Initialize the database
    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    # Clean up
    os.unlink(tmp_db.name)


@pytest.fixture
def sample_books(client):
    """Create sample books for testing."""
    books_data = [
        {'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald', 'year': 1925, 'isbn': '978-0743273565'},
        {'title': '1984', 'author': 'George Orwell', 'year': 1949, 'isbn': '978-0451524935'},
        {'title': 'To Kill a Mockingbird', 'author': 'Harper Lee', 'year': 1960, 'isbn': '978-0061120084'},
    ]
    created = []
    for book_data in books_data:
        response = client.post('/books', json=book_data)
        assert response.status_code == 201
        data = json.loads(response.data)
        created.append(data)
    return created


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the health endpoint exists, when called, then returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test the POST /books endpoint."""

    def test_create_book_success(self, client):
        """Given valid book data, when creating a book, then returns 201 with book details."""
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949,
            'isbn': '978-0451524935'
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == '1984'
        assert data['author'] == 'George Orwell'
        assert data['year'] == 1949
        assert data['isbn'] == '978-0451524935'
        assert 'id' in data

    def test_create_book_missing_title(self, client):
        """Given missing title, when creating a book, then returns 400 error."""
        book_data = {
            'author': 'George Orwell',
            'year': 1949,
            'isbn': '978-0451524935'
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given missing author, when creating a book, then returns 400 error."""
        book_data = {
            'title': '1984',
            'year': 1949,
            'isbn': '978-0451524935'
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_book_empty_body(self, client):
        """Given empty body, when creating a book, then returns 400 error."""
        response = client.post('/books', content_type='application/json', data='')
        assert response.status_code == 400


class TestListBooks:
    """Test the GET /books endpoint."""

    def test_list_books_empty(self, client):
        """Given no books exist, when listing books, then returns empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client, sample_books):
        """Given books exist, when listing books, then returns all books."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client, sample_books):
        """Given books exist, when filtering by author, then returns matching books."""
        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['author'] == 'George Orwell'

    def test_list_books_filter_no_match(self, client, sample_books):
        """Given books exist, when filtering by non-existent author, then returns empty list."""
        response = client.get('/books?author=NonExistent')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 0


class TestGetBook:
    """Test the GET /books/{id} endpoint."""

    def test_get_book_success(self, client, sample_books):
        """Given a book exists, when getting by ID, then returns the book."""
        book_id = sample_books[0]['id']
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby'
        assert data['id'] == book_id

    def test_get_book_not_found(self, client):
        """Given a book does not exist, when getting by ID, then returns 404."""
        response = client.get('/books/9999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestUpdateBook:
    """Test the PUT /books/{id} endpoint."""

    def test_update_book_success(self, client, sample_books):
        """Given a book exists, when updating it, then returns updated book."""
        book_id = sample_books[0]['id']
        update_data = {
            'title': 'The Great Gatsby (Updated)',
            'author': 'F. Scott Fitzgerald'
        }
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'The Great Gatsby (Updated)'

    def test_update_book_not_found(self, client):
        """Given a book does not exist, when updating it, then returns 404."""
        response = client.put('/books/9999', json={'title': 'Test'})
        assert response.status_code == 404

    def test_update_book_missing_title(self, client, sample_books):
        """Given a book exists, when updating with empty title, then returns 400."""
        book_id = sample_books[0]['id']
        update_data = {
            'title': '',
            'author': 'F. Scott Fitzgerald'
        }
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 400


class TestDeleteBook:
    """Test the DELETE /books/{id} endpoint."""

    def test_delete_book_success(self, client, sample_books):
        """Given a book exists, when deleting it, then returns success message."""
        book_id = sample_books[0]['id']
        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

    def test_delete_book_not_found(self, client):
        """Given a book does not exist, when deleting it, then returns 404."""
        response = client.delete('/books/9999')
        assert response.status_code == 404

    def test_delete_book_then_verify_removed(self, client, sample_books):
        """Given a book exists, when deleting it, then it is no longer in the list."""
        book_id = sample_books[0]['id']
        client.delete(f'/books/{book_id}')
        response = client.get('/books')
        data = json.loads(response.data)
        assert len(data) == 2
