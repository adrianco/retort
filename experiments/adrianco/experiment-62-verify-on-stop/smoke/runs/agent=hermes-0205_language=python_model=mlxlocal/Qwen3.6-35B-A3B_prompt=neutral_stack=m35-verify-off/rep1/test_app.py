import os
import pytest
import json
import tempfile
import copy

# Import the app module
import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    original_db = app_module.DATABASE

    # Create a temporary database file
    fd, temp_db = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Override the database path
    app_module.DATABASE = temp_db

    # Re-initialize the database with the temp file
    app_module.init_db()

    app_module.app.config['TESTING'] = True

    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    os.unlink(temp_db)
    app_module.DATABASE = original_db


def test_health_check(client):
    """Test the health check endpoint returns 200 and healthy status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_create_book_success(client):
    """Test creating a new book with all fields returns 201."""
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


def test_create_book_required_fields(client):
    """Test that creating a book without title returns 400."""
    data = {'author': 'Some Author'}
    response = client.post('/books',
                           data=json.dumps(data),
                           content_type='application/json')
    assert response.status_code == 400
    error_data = json.loads(response.data)
    assert 'error' in error_data


def test_create_book_missing_author(client):
    """Test that creating a book without author returns 400."""
    data = {'title': 'Some Book'}
    response = client.post('/books',
                           data=json.dumps(data),
                           content_type='application/json')
    assert response.status_code == 400
    error_data = json.loads(response.data)
    assert 'error' in error_data


def test_create_book_empty_title(client):
    """Test that creating a book with empty title returns 400."""
    data = {'title': '', 'author': 'Some Author'}
    response = client.post('/books',
                           data=json.dumps(data),
                           content_type='application/json')
    assert response.status_code == 400


def test_list_books_empty(client):
    """Test listing books when the collection is empty."""
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []


def test_list_books_with_data(client):
    """Test listing books returns all created books."""
    # Create two books
    book1 = {'title': 'Book One', 'author': 'Author A', 'year': 2000, 'isbn': '111'}
    book2 = {'title': 'Book Two', 'author': 'Author B', 'year': 2010, 'isbn': '222'}
    client.post('/books', data=json.dumps(book1), content_type='application/json')
    client.post('/books', data=json.dumps(book2), content_type='application/json')

    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2


def test_list_books_filter_by_author(client):
    """Test filtering books by author name."""
    book1 = {'title': 'Book One', 'author': 'J.K. Rowling', 'year': 1997}
    book2 = {'title': 'Book Two', 'author': 'George Orwell', 'year': 1949}
    book3 = {'title': 'Book Three', 'author': 'J.R.R. Tolkien', 'year': 1954}
    client.post('/books', data=json.dumps(book1), content_type='application/json')
    client.post('/books', data=json.dumps(book2), content_type='application/json')
    client.post('/books', data=json.dumps(book3), content_type='application/json')

    response = client.get('/books?author=Rowling')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['author'] == 'J.K. Rowling'


def test_get_book_by_id(client):
    """Test getting a single book by ID."""
    book = {'title': '1984', 'author': 'George Orwell', 'year': 1949}
    create_resp = client.post('/books', data=json.dumps(book), content_type='application/json')
    created_book = json.loads(create_resp.data)
    book_id = created_book['id']

    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'


def test_get_book_not_found(client):
    """Test getting a non-existent book returns 404."""
    response = client.get('/books/9999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_update_book(client):
    """Test updating an existing book."""
    book = {'title': 'Old Title', 'author': 'Old Author', 'year': 2000}
    create_resp = client.post('/books', data=json.dumps(book), content_type='application/json')
    created_book = json.loads(create_resp.data)
    book_id = created_book['id']

    update_data = {'title': 'New Title', 'author': 'New Author', 'year': 2020, 'isbn': '123-456'}
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'New Title'
    assert data['author'] == 'New Author'
    assert data['year'] == 2020
    assert data['isbn'] == '123-456'


def test_update_book_partial(client):
    """Test updating only some fields of a book."""
    book = {'title': 'Old Title', 'author': 'Old Author', 'year': 2000}
    create_resp = client.post('/books', data=json.dumps(book), content_type='application/json')
    created_book = json.loads(create_resp.data)
    book_id = created_book['id']

    update_data = {'title': 'Updated Title'}
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Old Author'
    assert data['year'] == 2000


def test_update_book_not_found(client):
    """Test updating a non-existent book returns 404."""
    update_data = {'title': 'New Title', 'author': 'New Author'}
    response = client.put('/books/9999',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 404


def test_delete_book(client):
    """Test deleting an existing book."""
    book = {'title': 'To Delete', 'author': 'Author', 'year': 2020}
    create_resp = client.post('/books', data=json.dumps(book), content_type='application/json')
    created_book = json.loads(create_resp.data)
    book_id = created_book['id']

    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data

    # Verify the book is gone
    get_response = client.get(f'/books/{book_id}')
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book returns 404."""
    response = client.delete('/books/9999')
    assert response.status_code == 404


def test_invalid_year(client):
    """Test that a non-integer year returns 400."""
    data = {'title': 'Bad Year', 'author': 'Author', 'year': 'not a number'}
    response = client.post('/books',
                           data=json.dumps(data),
                           content_type='application/json')
    assert response.status_code == 400


def test_create_book_without_optional_fields(client):
    """Test creating a book without optional fields (year, isbn)."""
    data = {'title': 'Minimal Book', 'author': 'Author'}
    response = client.post('/books',
                           data=json.dumps(data),
                           content_type='application/json')
    assert response.status_code == 201
    book = json.loads(response.data)
    assert book['title'] == 'Minimal Book'
    assert book['author'] == 'Author'
    assert book['year'] is None
    assert book['isbn'] is None
