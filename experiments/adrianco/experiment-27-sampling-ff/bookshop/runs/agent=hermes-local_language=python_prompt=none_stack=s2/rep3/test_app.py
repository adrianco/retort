"""Acceptance tests for the Book API REST Service."""

import pytest
import os
import sys
import json

# Add the project directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app


@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database."""
    app_instance = app.create_app(':memory:')

    with app_instance.test_client() as client:
        yield client


@pytest.fixture
def sample_books():
    """Provide sample book data."""
    return [
        {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        },
        {
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'year': 1960,
            'isbn': '978-0061120084'
        },
        {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949,
            'isbn': '978-0451524935'
        }
    ]


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the API is running, when I call GET /health, then it returns 200."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_check_returns_json(self, client):
        """Given the API is running, when I call GET /health, then it returns JSON with status."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test the POST /books endpoint."""

    def test_create_book_success(self, client):
        """Given no books exist, when I POST a new book with all fields, then it returns 201."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books', data=json.dumps(data), content_type='application/json')
        assert response.status_code == 201

    def test_create_book_returns_id(self, client):
        """Given a new book is created, when I POST it, then the response includes an id."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books', data=json.dumps(data), content_type='application/json')
        result = json.loads(response.data)
        assert 'id' in result
        assert isinstance(result['id'], int)

    def test_create_book_missing_title(self, client):
        """Given a book creation request without title, when I POST it, then it returns 400."""
        data = {
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books', data=json.dumps(data), content_type='application/json')
        assert response.status_code == 400

    def test_create_book_missing_author(self, client):
        """Given a book creation request without author, when I POST it, then it returns 400."""
        data = {
            'title': 'The Great Gatsby',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books', data=json.dumps(data), content_type='application/json')
        assert response.status_code == 400

    def test_create_book_partial_fields(self, client):
        """Given a book creation request with only required fields, when I POST it, then it returns 201."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald'
        }
        response = client.post('/books', data=json.dumps(data), content_type='application/json')
        assert response.status_code == 201


class TestListBooks:
    """Test the GET /books endpoint."""

    def test_list_books_empty(self, client):
        """Given no books exist, when I GET /books, then it returns an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_books_with_data(self, client, sample_books):
        """Given books exist in the database, when I GET /books, then it returns all books."""
        for book_data in sample_books:
            client.post('/books', data=json.dumps(book_data), content_type='application/json')

        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client, sample_books):
        """Given books exist with different authors, when I GET /books?author=Orwell, then it returns only matching books."""
        for book_data in sample_books:
            client.post('/books', data=json.dumps(book_data), content_type='application/json')

        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['author'] == 'George Orwell'

    def test_list_books_filter_no_match(self, client, sample_books):
        """Given books exist with different authors, when I GET /books?author=NonExistent, then it returns an empty list."""
        for book_data in sample_books:
            client.post('/books', data=json.dumps(book_data), content_type='application/json')

        response = client.get('/books?author=NonExistent')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 0


class TestGetBook:
    """Test the GET /books/{id} endpoint."""

    def test_get_book_success(self, client):
        """Given a book exists, when I GET /books/1, then it returns the book."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.post('/books', data=json.dumps(data), content_type='application/json')

        response = client.get('/books/1')
        assert response.status_code == 200

    def test_get_book_returns_correct_data(self, client):
        """Given a book exists with specific data, when I GET /books/1, then it returns the correct title and author."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.post('/books', data=json.dumps(data), content_type='application/json')

        response = client.get('/books/1')
        result = json.loads(response.data)
        assert result['title'] == 'The Great Gatsby'
        assert result['author'] == 'F. Scott Fitzgerald'

    def test_get_book_not_found(self, client):
        """Given no book with id 999 exists, when I GET /books/999, then it returns 404."""
        response = client.get('/books/999')
        assert response.status_code == 404


class TestUpdateBook:
    """Test the PUT /books/{id} endpoint."""

    def test_update_book_success(self, client):
        """Given a book exists, when I PUT updated data to /books/1, then it returns 200."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.post('/books', data=json.dumps(data), content_type='application/json')

        update_data = {
            'title': 'The Great Gatsby (Updated)',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.put('/books/1', data=json.dumps(update_data), content_type='application/json')
        assert response.status_code == 200

    def test_update_book_changes_data(self, client):
        """Given a book exists with old data, when I PUT new title, then the title is updated."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.post('/books', data=json.dumps(data), content_type='application/json')

        update_data = {
            'title': 'The Great Gatsby (Updated)',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.put('/books/1', data=json.dumps(update_data), content_type='application/json')

        response = client.get('/books/1')
        result = json.loads(response.data)
        assert result['title'] == 'The Great Gatsby (Updated)'

    def test_update_book_not_found(self, client):
        """Given no book with id 999 exists, when I PUT to /books/999, then it returns 404."""
        update_data = {
            'title': 'Some Book',
            'author': 'Some Author'
        }
        response = client.put('/books/999', data=json.dumps(update_data), content_type='application/json')
        assert response.status_code == 404

    def test_update_book_missing_title(self, client):
        """Given a book exists, when I PUT with empty title, then it returns 400."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.post('/books', data=json.dumps(data), content_type='application/json')

        update_data = {
            'title': '',
            'author': 'F. Scott Fitzgerald'
        }
        response = client.put('/books/1', data=json.dumps(update_data), content_type='application/json')
        assert response.status_code == 400


class TestDeleteBook:
    """Test the DELETE /books/{id} endpoint."""

    def test_delete_book_success(self, client):
        """Given a book exists, when I DELETE /books/1, then it returns 200."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.post('/books', data=json.dumps(data), content_type='application/json')

        response = client.delete('/books/1')
        assert response.status_code == 200

    def test_delete_book_removes_from_list(self, client):
        """Given a book exists, when I DELETE it, then GET /books no longer returns it."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        client.post('/books', data=json.dumps(data), content_type='application/json')

        client.delete('/books/1')

        response = client.get('/books')
        data = json.loads(response.data)
        assert len(data) == 0

    def test_delete_book_not_found(self, client):
        """Given no book with id 999 exists, when I DELETE /books/999, then it returns 404."""
        response = client.delete('/books/999')
        assert response.status_code == 404


class TestIntegration:
    """Integration tests that test multiple endpoints together."""

    def test_full_crud_lifecycle(self, client):
        """Given an empty database, when I create-read-update-delete a book, then all operations succeed."""
        # CREATE
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        create_response = client.post('/books', data=json.dumps(data), content_type='application/json')
        assert create_response.status_code == 201

        # READ
        read_response = client.get('/books/1')
        assert read_response.status_code == 200
        book = json.loads(read_response.data)
        assert book['title'] == 'The Great Gatsby'

        # UPDATE
        update_data = {
            'title': book['title'],
            'author': book['author'],
            'year': 1926,
            'isbn': book['isbn']
        }
        update_response = client.put('/books/1', data=json.dumps(update_data), content_type='application/json')
        assert update_response.status_code == 200

        # Verify the update took effect
        read_response = client.get('/books/1')
        book = json.loads(read_response.data)
        assert book['year'] == 1926

        # DELETE
        delete_response = client.delete('/books/1')
        assert delete_response.status_code == 200

        # Verify deletion
        read_response = client.get('/books/1')
        assert read_response.status_code == 404

    def test_multiple_books_with_filter(self, client):
        """Given multiple books by different authors, when I filter by author, then only matching books are returned."""
        books = [
            {'title': '1984', 'author': 'George Orwell', 'year': 1949, 'isbn': '978-0451524935'},
            {'title': 'Animal Farm', 'author': 'George Orwell', 'year': 1945, 'isbn': '978-0451526342'},
            {'title': 'Brave New World', 'author': 'Aldous Huxley', 'year': 1932, 'isbn': '978-0060850524'},
        ]

        for book_data in books:
            client.post('/books', data=json.dumps(book_data), content_type='application/json')

        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2

    def test_validation_prevents_empty_requests(self, client):
        """Given an empty JSON body, when I POST to /books, then it returns 400."""
        response = client.post('/books', data=json.dumps({}), content_type='application/json')
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
