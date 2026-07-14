import os
import pytest
import json
import sys

# Remove the db file if it exists so tests start fresh
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')

# We need to import after cleaning up the db
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def clean_db():
    """Remove the database before each test to ensure a clean state."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


@pytest.fixture
def client():
    """Create a test client."""
    import app
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Given the API is running, when I call GET /health, then I should get 200 OK."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestCreateBook:
    """Test creating books via POST /books."""

    def test_create_book_success(self, client):
        """Given no books exist, when I POST a valid book, then I get 201 with book data."""
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books',
                               data=json.dumps(data),
                               content_type='application/json')
        assert response.status_code == 201
        book = json.loads(response.data)
        assert book['title'] == 'The Great Gatsby'
        assert book['author'] == 'F. Scott Fitzgerald'
        assert book['year'] == 1925
        assert book['isbn'] == '978-0743273565'
        assert 'id' in book

    def test_create_book_without_year(self, client):
        """Given no books exist, when I POST a book without year, then year is null."""
        data = {
            'title': '1984',
            'author': 'George Orwell',
            'isbn': '978-0451524935'
        }
        response = client.post('/books',
                               data=json.dumps(data),
                               content_type='application/json')
        assert response.status_code == 201
        book = json.loads(response.data)
        assert book['title'] == '1984'
        assert book['year'] is None

    def test_create_book_missing_title(self, client):
        """Given no books exist, when I POST a book without title, then I get 400."""
        data = {
            'author': 'Some Author',
            'year': 2020
        }
        response = client.post('/books',
                               data=json.dumps(data),
                               content_type='application/json')
        assert response.status_code == 400
        errors = json.loads(response.data)
        assert 'title' in errors

    def test_create_book_missing_author(self, client):
        """Given no books exist, when I POST a book without author, then I get 400."""
        data = {
            'title': 'Some Book',
            'year': 2020
        }
        response = client.post('/books',
                               data=json.dumps(data),
                               content_type='application/json')
        assert response.status_code == 400
        errors = json.loads(response.data)
        assert 'author' in errors

    def test_create_book_empty_body(self, client):
        """Given no books exist, when I POST with empty body, then I get 400."""
        response = client.post('/books',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400


class TestListBooks:
    """Test listing books via GET /books."""

    def test_list_books_empty(self, client):
        """Given no books exist, when I GET /books, then I get an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client):
        """Given 3 books exist, when I GET /books, then I get all 3 books."""
        # Create 3 books
        for i in range(3):
            client.post('/books', data=json.dumps({
                'title': f'Book {i}',
                'author': f'Author {i}',
                'year': 2020 + i
            }), content_type='application/json')

        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client):
        """Given 3 books by 2 different authors, when I GET /books?author=Author1, then I get only Author1's books."""
        client.post('/books', data=json.dumps({
            'title': 'Book A', 'author': 'Author1', 'year': 2020
        }), content_type='application/json')
        client.post('/books', data=json.dumps({
            'title': 'Book B', 'author': 'Author1', 'year': 2021
        }), content_type='application/json')
        client.post('/books', data=json.dumps({
            'title': 'Book C', 'author': 'Author2', 'year': 2022
        }), content_type='application/json')

        response = client.get('/books?author=Author1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        for book in data:
            assert 'Author1' in book['author']


class TestGetBook:
    """Test getting a single book via GET /books/<id>."""

    def test_get_existing_book(self, client):
        """Given a book exists, when I GET /books/1, then I get the book data."""
        resp = client.post('/books', data=json.dumps({
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'year': 1960,
            'isbn': '978-0061120084'
        }), content_type='application/json')
        book_id = json.loads(resp.data)['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'To Kill a Mockingbird'
        assert data['author'] == 'Harper Lee'

    def test_get_nonexistent_book(self, client):
        """Given no book with id 999, when I GET /books/999, then I get 404."""
        response = client.get('/books/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestUpdateBook:
    """Test updating a book via PUT /books/<id>."""

    def test_update_book_success(self, client):
        """Given a book exists, when I PUT updated data, then I get the updated book."""
        resp = client.post('/books', data=json.dumps({
            'title': 'Original Title',
            'author': 'Original Author',
            'year': 2000
        }), content_type='application/json')
        book_id = json.loads(resp.data)['id']

        response = client.put(f'/books/{book_id}', data=json.dumps({
            'title': 'Updated Title',
            'author': 'Updated Author'
        }), content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Updated Title'
        assert data['author'] == 'Updated Author'
        assert data['year'] == 2000  # unchanged

    def test_update_nonexistent_book(self, client):
        """Given no book with id 999, when I PUT /books/999, then I get 404."""
        response = client.put('/books/999', data=json.dumps({
            'title': 'Ghost'
        }), content_type='application/json')
        assert response.status_code == 404

    def test_update_book_missing_required_fields(self, client):
        """Given a book exists, when I PUT with empty title, then I get 400."""
        resp = client.post('/books', data=json.dumps({
            'title': 'Original Title',
            'author': 'Original Author',
            'year': 2000
        }), content_type='application/json')
        book_id = json.loads(resp.data)['id']

        response = client.put(f'/books/{book_id}', data=json.dumps({
            'title': '',
            'author': 'Updated Author'
        }), content_type='application/json')
        assert response.status_code == 400


class TestDeleteBook:
    """Test deleting a book via DELETE /books/<id>."""

    def test_delete_existing_book(self, client):
        """Given a book exists, when I DELETE /books/1, then I get 200 and the book is gone."""
        resp = client.post('/books', data=json.dumps({
            'title': 'To Delete',
            'author': 'Author',
            'year': 2020
        }), content_type='application/json')
        book_id = json.loads(resp.data)['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify book is gone
        get_response = client.get(f'/books/{book_id}')
        assert get_response.status_code == 404

    def test_delete_nonexistent_book(self, client):
        """Given no book with id 999, when I DELETE /books/999, then I get 404."""
        response = client.delete('/books/999')
        assert response.status_code == 404


class TestIntegration:
    """Integration test: full CRUD lifecycle."""

    def test_full_crud_lifecycle(self, client):
        """Given no books, when I create, read, update, list, and delete a book, then all operations succeed."""
        # CREATE
        resp = client.post('/books', data=json.dumps({
            'title': 'War and Peace',
            'author': 'Leo Tolstoy',
            'year': 1869,
            'isbn': '978-0199232765'
        }), content_type='application/json')
        assert resp.status_code == 201
        book_id = json.loads(resp.data)['id']

        # READ
        resp = client.get(f'/books/{book_id}')
        assert resp.status_code == 200
        assert json.loads(resp.data)['title'] == 'War and Peace'

        # LIST
        resp = client.get('/books')
        assert resp.status_code == 200
        assert len(json.loads(resp.data)) == 1

        # UPDATE
        resp = client.put(f'/books/{book_id}', data=json.dumps({
            'title': 'War and Peace (Updated)'
        }), content_type='application/json')
        assert resp.status_code == 200
        assert json.loads(resp.data)['title'] == 'War and Peace (Updated)'

        # DELETE
        resp = client.delete(f'/books/{book_id}')
        assert resp.status_code == 200

        # Verify deletion
        resp = client.get(f'/books/{book_id}')
        assert resp.status_code == 404
