import os
import sys
import tempfile
import pytest

# Add the current directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as book_app


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    db_fd, temp_db = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    book_app.DATABASE = temp_db
    # Re-initialize the DB with the test database
    book_app.init_db()

    book_app.app.config['TESTING'] = True

    with book_app.app.test_client() as client:
        yield client

    os.unlink(temp_db)


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the health endpoint exists, When I GET /health, Then it returns 200."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_check_returns_healthy_status(self, client):
        """Given the health endpoint exists, When I GET /health, Then status is healthy."""
        response = client.get('/health')
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test the POST /books endpoint."""

    def test_create_book_success(self, client):
        """Given no books exist, When I POST a valid book, Then it returns 201 with the book."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books', json=data)
        assert response.status_code == 201

        book = response.get_json()
        assert book['title'] == 'The Great Gatsby'
        assert book['author'] == 'F. Scott Fitzgerald'
        assert book['year'] == 1925
        assert book['isbn'] == '978-0743273565'
        assert book['id'] is not None

    def test_create_book_missing_title(self, client):
        """Given no books exist, When I POST without title, Then it returns 400."""
        data = {
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
        }
        response = client.post('/books', json=data)
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_create_book_missing_author(self, client):
        """Given no books exist, When I POST without author, Then it returns 400."""
        data = {
            'title': 'The Great Gatsby',
            'year': 1925,
        }
        response = client.post('/books', json=data)
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_create_book_with_optional_fields(self, client):
        """Given no books exist, When I POST with only title and author, Then it returns 201."""
        data = {
            'title': 'Test Book',
            'author': 'Test Author'
        }
        response = client.post('/books', json=data)
        assert response.status_code == 201
        book = response.get_json()
        assert book['year'] is None
        assert book['isbn'] is None

    def test_create_book_invalid_year(self, client):
        """Given no books exist, When I POST with non-integer year, Then it returns 400."""
        data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 'not a number'
        }
        response = client.post('/books', json=data)
        assert response.status_code == 400


class TestListBooks:
    """Test the GET /books endpoint."""

    def test_list_books_empty(self, client):
        """Given no books exist, When I GET /books, Then it returns an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_with_data(self, client):
        """Given books exist, When I GET /books, Then it returns all books."""
        # Create two books
        client.post('/books', json={
            'title': 'Book One', 'author': 'Author A'
        })
        client.post('/books', json={
            'title': 'Book Two', 'author': 'Author B'
        })

        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given multiple books exist, When I GET /books?author=X, Then only matching books are returned."""
        client.post('/books', json={
            'title': 'Book One', 'author': 'J.K. Rowling'
        })
        client.post('/books', json={
            'title': 'Book Two', 'author': 'George Orwell'
        })
        client.post('/books', json={
            'title': 'Book Three', 'author': 'J.R.R. Tolkien'
        })

        response = client.get('/books?author=Rowling')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['author'] == 'J.K. Rowling'


class TestGetBook:
    """Test the GET /books/{id} endpoint."""

    def test_get_book_success(self, client):
        """Given a book exists, When I GET /books/{id}, Then it returns the book."""
        create_resp = client.post('/books', json={
            'title': '1984', 'author': 'George Orwell', 'year': 1949
        })
        book_id = create_resp.get_json()['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == '1984'

    def test_get_book_not_found(self, client):
        """Given no book with that ID exists, When I GET /books/999, Then it returns 404."""
        response = client.get('/books/999')
        assert response.status_code == 404


class TestUpdateBook:
    """Test the PUT /books/{id} endpoint."""

    def test_update_book_success(self, client):
        """Given a book exists, When I PUT updated data, Then it returns the updated book."""
        create_resp = client.post('/books', json={
            'title': 'Old Title', 'author': 'Old Author'
        })
        book_id = create_resp.get_json()['id']

        response = client.put(f'/books/{book_id}', json={
            'title': 'New Title', 'author': 'New Author'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'New Title'
        assert data['author'] == 'New Author'

    def test_update_book_not_found(self, client):
        """Given no book with that ID exists, When I PUT /books/999, Then it returns 404."""
        response = client.put('/books/999', json={
            'title': 'New Title', 'author': 'New Author'
        })
        assert response.status_code == 404

    def test_update_book_partial(self, client):
        """Given a book exists with year and isbn, When I PUT only title, Then year/isbn are preserved."""
        create_resp = client.post('/books', json={
            'title': 'Old Title', 'author': 'Author', 'year': 2000, 'isbn': '123'
        })
        book_id = create_resp.get_json()['id']

        response = client.put(f'/books/{book_id}', json={
            'title': 'New Title'
        })
        data = response.get_json()
        assert data['title'] == 'New Title'
        assert data['year'] == 2000
        assert data['isbn'] == '123'


class TestDeleteBook:
    """Test the DELETE /books/{id} endpoint."""

    def test_delete_book_success(self, client):
        """Given a book exists, When I DELETE /books/{id}, Then it returns 200 and the book is gone."""
        create_resp = client.post('/books', json={
            'title': 'To Delete', 'author': 'Author'
        })
        book_id = create_resp.get_json()['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200

        # Verify the book is gone
        get_resp = client.get(f'/books/{book_id}')
        assert get_resp.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given no book with that ID exists, When I DELETE /books/999, Then it returns 404."""
        response = client.delete('/books/999')
        assert response.status_code == 404
