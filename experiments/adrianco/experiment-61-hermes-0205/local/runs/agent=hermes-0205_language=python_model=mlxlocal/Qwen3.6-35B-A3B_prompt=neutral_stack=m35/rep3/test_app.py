import os
import pytest
import json
import tempfile

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database file."""
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()

    app_module.DATABASE = tmp.name
    app_module._db_initialized = False
    app_module.init_db()
    app_module.app.config['TESTING'] = True

    with app_module.app.test_client() as test_client:
        yield test_client

    # Cleanup
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


# --- Health Check Tests ---

class TestHealthCheck:
    def test_health_returns_200(self, client):
        """Given the app is running, when I call GET /health, then I get 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


# --- Create Book Tests ---

class TestCreateBook:
    def test_create_book_success(self, client):
        """Given valid book data, when I POST /books, then I get 201 with the book."""
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
        book = response.get_json()
        assert book['title'] == 'The Great Gatsby'
        assert book['author'] == 'F. Scott Fitzgerald'
        assert book['year'] == 1925
        assert book['isbn'] == '978-0743273565'
        assert book['id'] is not None

    def test_create_book_missing_title(self, client):
        """Given missing title, when I POST /books, then I get 400 error."""
        data = {
            'author': 'Unknown Author',
            'year': 2000
        }
        response = client.post('/books',
                               data=json.dumps(data),
                               content_type='application/json')
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_create_book_missing_author(self, client):
        """Given missing author, when I POST /books, then I get 400 error."""
        data = {
            'title': 'Some Book'
        }
        response = client.post('/books',
                               data=json.dumps(data),
                               content_type='application/json')
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_create_book_without_isbn(self, client):
        """Given book data without ISBN, when I POST /books, then I get 201."""
        data = {
            'title': 'Python Crash Course',
            'author': 'Eric Matthes',
            'year': 2019
        }
        response = client.post('/books',
                               data=json.dumps(data),
                               content_type='application/json')
        assert response.status_code == 201
        book = response.get_json()
        assert book['isbn'] is None


# --- List Books Tests ---

class TestListBooks:
    def test_list_books_empty(self, client):
        """Given no books, when I GET /books, then I get an empty list."""
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_list_books_with_data(self, client):
        """Given two books exist, when I GET /books, then I get both books."""
        # Create first book
        client.post('/books',
                    data=json.dumps({'title': 'Book A', 'author': 'Author X',
                                     'year': 2000}),
                    content_type='application/json')
        # Create second book
        client.post('/books',
                    data=json.dumps({'title': 'Book B', 'author': 'Author Y',
                                     'year': 2010}),
                    content_type='application/json')

        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given multiple books, when I GET /books?author=X, then I get filtered results."""
        client.post('/books',
                    data=json.dumps({'title': 'Book A', 'author': 'J.K. Rowling',
                                     'year': 1997}),
                    content_type='application/json')
        client.post('/books',
                    data=json.dumps({'title': 'Book B', 'author': 'J.K. Rowling',
                                     'year': 1998}),
                    content_type='application/json')
        client.post('/books',
                    data=json.dumps({'title': 'Book C', 'author': 'George Orwell',
                                     'year': 1949}),
                    content_type='application/json')

        response = client.get('/books?author=Rowling')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert 'Rowling' in book['author']


# --- Get Single Book Tests ---

class TestGetBook:
    def test_get_book_by_id(self, client):
        """Given a book exists, when I GET /books/{id}, then I get the book."""
        resp = client.post('/books',
                           data=json.dumps({'title': '1984', 'author': 'George Orwell',
                                            'year': 1949, 'isbn': '978-0451524935'}),
                           content_type='application/json')
        book_id = resp.get_json()['id']

        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == '1984'
        assert data['author'] == 'George Orwell'

    def test_get_book_not_found(self, client):
        """Given a non-existent book, when I GET /books/{id}, then I get 404."""
        response = client.get('/books/9999')
        assert response.status_code == 404
        assert 'error' in response.get_json()


# --- Update Book Tests ---

class TestUpdateBook:
    def test_update_book_success(self, client):
        """Given a book exists, when I PUT /books/{id}, then I get the updated book."""
        resp = client.post('/books',
                           data=json.dumps({'title': 'Old Title', 'author': 'Old Author',
                                            'year': 2000}),
                           content_type='application/json')
        book_id = resp.get_json()['id']

        response = client.put(f'/books/{book_id}',
                              data=json.dumps({'title': 'New Title', 'year': 2024}),
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'New Title'
        assert data['author'] == 'Old Author'  # unchanged
        assert data['year'] == 2024

    def test_update_book_not_found(self, client):
        """Given a non-existent book, when I PUT /books/{id}, then I get 404."""
        response = client.put('/books/9999',
                              data=json.dumps({'title': 'X'}),
                              content_type='application/json')
        assert response.status_code == 404

    def test_update_book_partial_fields(self, client):
        """Given a book exists, when I PUT with partial fields, then existing fields are preserved."""
        resp = client.post('/books',
                           data=json.dumps({'title': 'Some Book', 'author': 'Some Author',
                                            'year': 2000}),
                           content_type='application/json')
        book_id = resp.get_json()['id']

        # Update only author - title should be preserved
        response = client.put(f'/books/{book_id}',
                              data=json.dumps({'author': 'New Author'}),
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Some Book'  # preserved
        assert data['author'] == 'New Author'


# --- Delete Book Tests ---

class TestDeleteBook:
    def test_delete_book_success(self, client):
        """Given a book exists, when I DELETE /books/{id}, then I get 200 and it's gone."""
        resp = client.post('/books',
                           data=json.dumps({'title': 'ToDelete', 'author': 'Author',
                                            'year': 2020}),
                           content_type='application/json')
        book_id = resp.get_json()['id']

        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        assert 'message' in response.get_json()

        # Verify it's gone
        get_resp = client.get(f'/books/{book_id}')
        assert get_resp.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a non-existent book, when I DELETE /books/{id}, then I get 404."""
        response = client.delete('/books/9999')
        assert response.status_code == 404
