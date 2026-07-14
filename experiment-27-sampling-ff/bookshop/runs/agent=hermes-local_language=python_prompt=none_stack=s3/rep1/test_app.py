import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db, DATABASE


@pytest.fixture
def client():
    """Create a test client with a fresh database."""
    # Use an in-memory or temp database for testing
    test_db = DATABASE.replace('books.db', 'test_books.db')

    app.config['TESTING'] = True

    # Remove old test db if exists
    if os.path.exists(test_db):
        os.remove(test_db)

    # Override database path for testing
    import app as app_module
    original_db = app_module.DATABASE
    app_module.DATABASE = test_db

    # Reinitialize the DB with the new path
    init_db()

    app_module.app.config['DATABASE'] = test_db

    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)

    app_module.DATABASE = original_db


@pytest.fixture
def sample_book():
    """Return a sample book payload."""
    return {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565"
    }


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the health endpoint exists, When I call GET /health, Then it returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test creating books."""

    def test_create_book_success(self, client, sample_book):
        """Given valid book data, When I POST /books, Then it returns 201 with the book."""
        response = client.post('/books', json=sample_book)
        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == sample_book['title']
        assert data['author'] == sample_book['author']
        assert data['year'] == sample_book['year']
        assert data['isbn'] == sample_book['isbn']
        assert 'id' in data

    def test_create_book_missing_title(self, client):
        """Given missing title, When I POST /books, Then it returns 400."""
        response = client.post('/books', json={"author": "Test Author"})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_missing_author(self, client):
        """Given missing author, When I POST /books, Then it returns 400."""
        response = client.post('/books', json={"title": "Test Book"})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_book_no_body(self, client):
        """Given no request body, When I POST /books, Then it returns 415 (unsupported media type)."""
        response = client.post('/books', json=None)
        assert response.status_code == 415


class TestListBooks:
    """Test listing books."""

    def test_list_books_empty(self, client):
        """Given no books exist, When I GET /books, Then it returns an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_books_with_data(self, client, sample_book):
        """Given books exist, When I GET /books, Then it returns all books."""
        client.post('/books', json=sample_book)
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1

    def test_list_books_filter_by_author(self, client):
        """Given multiple books by different authors, When I GET /books?author=filter, Then it returns filtered results."""
        book1 = {"title": "Book One", "author": "Author A", "year": 2020}
        book2 = {"title": "Book Two", "author": "Author B", "year": 2021}
        book3 = {"title": "Book Three", "author": "Author A", "year": 2022}

        client.post('/books', json=book1)
        client.post('/books', json=book2)
        client.post('/books', json=book3)

        response = client.get('/books?author=Author A')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2


class TestGetBook:
    """Test getting a single book."""

    def test_get_book_success(self, client, sample_book):
        """Given a book exists, When I GET /books/{id}, Then it returns the book."""
        create_resp = client.post('/books', json=sample_book)
        book_id = create_resp.get_json()['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == sample_book['title']

    def test_get_book_not_found(self, client):
        """Given a book does not exist, When I GET /books/{id}, Then it returns 404."""
        response = client.get('/books/999')
        assert response.status_code == 404


class TestUpdateBook:
    """Test updating a book."""

    def test_update_book_success(self, client, sample_book):
        """Given a book exists, When I PUT /books/{id}, Then it returns the updated book."""
        create_resp = client.post('/books', json=sample_book)
        book_id = create_resp.get_json()['id']

        update_data = {"title": "Updated Title", "author": sample_book['author']}
        response = client.put(f'/books/{book_id}', json=update_data)

        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Updated Title'

    def test_update_book_not_found(self, client):
        """Given a book does not exist, When I PUT /books/{id}, Then it returns 404."""
        response = client.put('/books/999', json={"title": "New Title"})
        assert response.status_code == 404


class TestDeleteBook:
    """Test deleting a book."""

    def test_delete_book_success(self, client, sample_book):
        """Given a book exists, When I DELETE /books/{id}, Then it returns 200 and the book is gone."""
        create_resp = client.post('/books', json=sample_book)
        book_id = create_resp.get_json()['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200

        # Verify the book is gone
        get_response = client.get(f'/books/{book_id}')
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a book does not exist, When I DELETE /books/{id}, Then it returns 404."""
        response = client.delete('/books/999')
        assert response.status_code == 404


class TestDuplicateISBN:
    """Test duplicate ISBN handling."""

    def test_create_book_duplicate_isbn(self, client, sample_book):
        """Given a book with an ISBN exists, When I POST /books with same ISBN, Then it returns 409."""
        client.post('/books', json=sample_book)
        response = client.post('/books', json=sample_book)
        assert response.status_code == 409


class TestIntegration:
    """Integration tests for full CRUD workflow."""

    def test_full_crud_workflow(self, client):
        """Given a fresh database, When I perform full CRUD operations, Then all steps succeed."""
        # CREATE
        book = {
            "title": "1984",
            "author": "George Orwell",
            "year": 1949,
            "isbn": "978-0451524935"
        }
        create_resp = client.post('/books', json=book)
        assert create_resp.status_code == 201
        book_id = create_resp.get_json()['id']

        # READ
        get_resp = client.get(f'/books/{book_id}')
        assert get_resp.status_code == 200
        assert get_resp.get_json()['title'] == '1984'

        # UPDATE
        update_data = {"title": "Nineteen Eighty-Four", "author": book['author']}
        update_resp = client.put(f'/books/{book_id}', json=update_data)
        assert update_resp.status_code == 200
        assert update_resp.get_json()['title'] == 'Nineteen Eighty-Four'

        # DELETE
        delete_resp = client.delete(f'/books/{book_id}')
        assert delete_resp.status_code == 200

        # Verify deletion
        get_after_delete = client.get(f'/books/{book_id}')
        assert get_after_delete.status_code == 404
