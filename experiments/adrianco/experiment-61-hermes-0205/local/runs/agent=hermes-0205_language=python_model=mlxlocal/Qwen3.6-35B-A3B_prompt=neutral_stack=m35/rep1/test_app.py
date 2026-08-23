import os
import sys
import json
import tempfile
import pytest

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    original_db = app_module.DATABASE

    # Use a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        app_module.DATABASE = tmp.name

    app_module.init_db()
    app_module.app.config['TESTING'] = True

    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    app_module.DATABASE = original_db
    os.unlink(tmp.name)


def test_health_check(client):
    """Given the health endpoint is called, When no parameters are provided, Then it returns 200 with healthy status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_create_book(client):
    """Given a POST /books request with valid data, When submitted, Then it creates a book and returns 201."""
    data = {
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    }
    response = client.post('/books', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 201
    book = json.loads(response.data)
    assert book['title'] == 'The Great Gatsby'
    assert book['author'] == 'F. Scott Fitzgerald'
    assert book['year'] == 1925
    assert book['isbn'] == '978-0743273565'
    assert 'id' in book


def test_create_book_missing_title(client):
    """Given a POST /books request without title, When submitted, Then it returns 400 with error."""
    data = {
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    }
    response = client.post('/books', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 400
    error_data = json.loads(response.data)
    assert 'error' in error_data


def test_create_book_missing_author(client):
    """Given a POST /books request without author, When submitted, Then it returns 400 with error."""
    data = {
        'title': 'The Great Gatsby',
        'year': 1925,
        'isbn': '978-0743273565'
    }
    response = client.post('/books', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 400
    error_data = json.loads(response.data)
    assert 'error' in error_data


def test_list_books(client):
    """Given multiple books exist, When GET /books is called, Then it returns all books."""
    # Create two books
    client.post('/books', data=json.dumps({'title': 'Book A', 'author': 'Author X', 'year': 2000}), content_type='application/json')
    client.post('/books', data=json.dumps({'title': 'Book B', 'author': 'Author Y', 'year': 2010}), content_type='application/json')

    response = client.get('/books')
    assert response.status_code == 200
    books = json.loads(response.data)
    assert len(books) == 2


def test_list_books_filter_by_author(client):
    """Given multiple books exist, When GET /books?author=X is called, Then it returns only matching books."""
    client.post('/books', data=json.dumps({'title': 'Book A', 'author': 'Author X', 'year': 2000}), content_type='application/json')
    client.post('/books', data=json.dumps({'title': 'Book B', 'author': 'Author Y', 'year': 2010}), content_type='application/json')
    client.post('/books', data=json.dumps({'title': 'Book C', 'author': 'Author X', 'year': 2020}), content_type='application/json')

    response = client.get('/books?author=Author+X')
    assert response.status_code == 200
    books = json.loads(response.data)
    assert len(books) == 2
    for book in books:
        assert 'Author X' in book['author']


def test_get_book_by_id(client):
    """Given a book exists, When GET /books/{id} is called, Then it returns the book."""
    resp = client.post('/books', data=json.dumps({'title': '1984', 'author': 'George Orwell', 'year': 1949}), content_type='application/json')
    book = json.loads(resp.data)
    book_id = book['id']

    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'


def test_get_book_not_found(client):
    """Given a non-existent book ID, When GET /books/{id} is called, Then it returns 404."""
    response = client.get('/books/9999')
    assert response.status_code == 404


def test_update_book(client):
    """Given a book exists, When PUT /books/{id} is called with new data, Then it returns the updated book."""
    resp = client.post('/books', data=json.dumps({'title': 'Original Title', 'author': 'Original Author', 'year': 2000}), content_type='application/json')
    book = json.loads(resp.data)
    book_id = book['id']

    response = client.put(f'/books/{book_id}', data=json.dumps({'title': 'Updated Title', 'author': 'Updated Author'}), content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Updated Author'
    assert data['year'] == 2000  # unchanged


def test_update_book_not_found(client):
    """Given a non-existent book ID, When PUT /books/{id} is called, Then it returns 404."""
    response = client.put('/books/9999', data=json.dumps({'title': 'Nope'}), content_type='application/json')
    assert response.status_code == 404


def test_delete_book(client):
    """Given a book exists, When DELETE /books/{id} is called, Then it returns 200 and the book is removed."""
    resp = client.post('/books', data=json.dumps({'title': 'To Delete', 'author': 'Someone', 'year': 2024}), content_type='application/json')
    book = json.loads(resp.data)
    book_id = book['id']

    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200

    # Verify it's gone
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404


def test_delete_book_not_found(client):
    """Given a non-existent book ID, When DELETE /books/{id} is called, Then it returns 404."""
    response = client.delete('/books/9999')
    assert response.status_code == 404


def test_create_book_empty_body(client):
    """Given a POST /books with no body, When submitted, Then it returns 400."""
    response = client.post('/books', content_type='application/json')
    assert response.status_code == 400


def test_create_book_with_minimal_data(client):
    """Given a POST /books with only title and author, When submitted, Then it creates the book with null year/isbn."""
    data = {'title': 'Minimal Book', 'author': 'Min Author'}
    response = client.post('/books', data=json.dumps(data), content_type='application/json')
    assert response.status_code == 201
    book = json.loads(response.data)
    assert book['title'] == 'Minimal Book'
    assert book['year'] is None
    assert book['isbn'] is None
