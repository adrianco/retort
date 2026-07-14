import os
import sys
import tempfile
import pytest

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    # Create a fresh temp db for each test
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    # Create the app with this specific test db
    test_app = app.create_app(test_db_path=db_path)
    test_app.config['TESTING'] = True

    with test_app.test_client() as client:
        yield client

    # Clean up the temp db
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sample_books(client):
    """Create some sample books for testing."""
    books = [
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"},
        {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"},
        {"title": "To Kill a Mockingbird", "author": "Harper Lee", "year": 1960, "isbn": "978-0061120084"},
    ]
    created = []
    for book_data in books:
        response = client.post('/books', json=book_data)
        assert response.status_code == 201
        created.append(response.get_json())
    return created


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the health endpoint exists, when we call it, then we get 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"


class TestCreateBook:
    """Test the create book endpoint."""

    def test_create_book_success(self, client):
        """Given valid book data, when we POST /books, then we get 201 with the book."""
        book_data = {
            "title": "Brave New World",
            "author": "Aldous Huxley",
            "year": 1932,
            "isbn": "978-0060850524"
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Brave New World"
        assert data["author"] == "Aldous Huxley"
        assert data["year"] == 1932
        assert data["isbn"] == "978-0060850524"
        assert "id" in data

    def test_create_book_missing_title(self, client):
        """Given no title, when we POST /books, then we get 400."""
        book_data = {
            "author": "Test Author",
            "year": 2020,
            "isbn": "123-456"
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given no author, when we POST /books, then we get 400."""
        book_data = {
            "title": "Test Book",
            "year": 2020,
            "isbn": "123-456"
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_book_empty_title(self, client):
        """Given empty title, when we POST /books, then we get 400."""
        book_data = {
            "title": "",
            "author": "Test Author"
        }
        response = client.post('/books', json=book_data)
        assert response.status_code == 400

    def test_create_book_without_json(self, client):
        """Given non-JSON body, when we POST /books, then we get 415 or 400."""
        response = client.post('/books', data='not json', content_type='text/plain')
        assert response.status_code in (400, 415)


class TestListBooks:
    """Test the list books endpoint."""

    def test_list_books_empty(self, client):
        """Given no books, when we GET /books, then we get an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_returns_all(self, client, sample_books):
        """Given books exist, when we GET /books, then we get all books."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client, sample_books):
        """Given books by different authors, when we GET /books?author=Orwell, then we get only matching books."""
        response = client.get('/books?author=Orwell')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["author"] == "George Orwell"

    def test_list_books_filter_no_match(self, client, sample_books):
        """Given books by different authors, when we GET /books?author=NonExistent, then we get empty list."""
        response = client.get('/books?author=NonExistentAuthor')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 0


class TestGetBook:
    """Test the get book by ID endpoint."""

    def test_get_book_success(self, client, sample_books):
        """Given a book exists, when we GET /books/{id}, then we get the book."""
        book_id = sample_books[0]["id"]
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == book_id
        assert data["title"] == "The Great Gatsby"

    def test_get_book_not_found(self, client):
        """Given a non-existent ID, when we GET /books/{id}, then we get 404."""
        response = client.get('/books/9999')
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestUpdateBook:
    """Test the update book endpoint."""

    def test_update_book_success(self, client, sample_books):
        """Given a book exists, when we PUT /books/{id}, then we get the updated book."""
        book_id = sample_books[0]["id"]
        update_data = {
            "title": "The Great Gatsby (Updated)",
            "author": "F. Scott Fitzgerald"
        }
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "The Great Gatsby (Updated)"

    def test_update_book_not_found(self, client):
        """Given a non-existent ID, when we PUT /books/{id}, then we get 404."""
        update_data = {"title": "Test", "author": "Test Author"}
        response = client.put('/books/9999', json=update_data)
        assert response.status_code == 404

    def test_update_book_partial_update(self, client, sample_books):
        """Given a book exists, when we PUT with only title, then only title is updated."""
        book_id = sample_books[0]["id"]
        update_data = {"title": "The Great Gatsby (Updated)"}
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "The Great Gatsby (Updated)"
        assert data["author"] == sample_books[0]["author"]

    def test_update_book_empty_title(self, client, sample_books):
        """Given a book exists, when we PUT with empty title, then we get 400."""
        book_id = sample_books[0]["id"]
        update_data = {"title": "", "author": "Test Author"}
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 400


class TestDeleteBook:
    """Test the delete book endpoint."""

    def test_delete_book_success(self, client, sample_books):
        """Given a book exists, when we DELETE /books/{id}, then we get 200 and the book is gone."""
        book_id = sample_books[0]["id"]
        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

        # Verify the book is actually deleted
        get_response = client.get(f'/books/{book_id}')
        assert get_response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a non-existent ID, when we DELETE /books/{id}, then we get 404."""
        response = client.delete('/books/9999')
        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
