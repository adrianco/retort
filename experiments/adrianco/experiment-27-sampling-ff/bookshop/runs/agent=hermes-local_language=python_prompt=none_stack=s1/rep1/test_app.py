import os
import sys
import tempfile
import pytest

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    import app as app_module

    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    # Patch the DATABASE path before init_db is called
    original_db = app_module.DATABASE
    app_module.DATABASE = db_path

    # Initialize the database with the temp path
    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    os.unlink(db_path)
    app_module.DATABASE = original_db


def test_health_check(client):
    """Given the health endpoint exists, when I call GET /health, then I get a 200 status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_create_book(client):
    """Given no books exist, when I POST a new book, then I get a 201 status with the book data."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == 'The Great Gatsby'
    assert data['author'] == 'F. Scott Fitzgerald'
    assert data['year'] == 1925
    assert data['isbn'] == '978-0743273565'
    assert 'id' in data


def test_create_book_missing_title(client):
    """Given a POST request without title, when I create a book, then I get a 400 error."""
    response = client.post('/books', json={
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_create_book_missing_author(client):
    """Given a POST request without author, when I create a book, then I get a 400 error."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'year': 1925
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_list_books(client):
    """Given multiple books exist, when I GET /books, then I get all books."""
    # Create some books
    client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    client.post('/books', json={
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949
    })
    client.post('/books', json={
        'title': 'Animal Farm',
        'author': 'George Orwell',
        'year': 1945
    })

    response = client.get('/books')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 3


def test_list_books_filter_by_author(client):
    """Given multiple books exist, when I GET /books?author=Orwell, then I get only Orwell's books."""
    client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    client.post('/books', json={
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949
    })
    client.post('/books', json={
        'title': 'Animal Farm',
        'author': 'George Orwell',
        'year': 1945
    })

    response = client.get('/books?author=Orwell')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    for book in data:
        assert 'Orwell' in book['author']


def test_get_book_by_id(client):
    """Given a book exists, when I GET /books/{id}, then I get the book data."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    book_id = response.get_json()['id']

    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'The Great Gatsby'
    assert data['id'] == book_id


def test_get_book_not_found(client):
    """Given a book doesn't exist, when I GET /books/999, then I get a 404 error."""
    response = client.get('/books/999')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_update_book(client):
    """Given a book exists, when I PUT updated data, then I get the updated book."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    book_id = response.get_json()['id']

    response = client.put(f'/books/{book_id}', json={
        'title': 'The Great Gatsby (Updated)',
        'year': 1926
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'The Great Gatsby (Updated)'
    assert data['year'] == 1926
    assert data['author'] == 'F. Scott Fitzgerald'  # unchanged


def test_update_book_not_found(client):
    """Given a book doesn't exist, when I PUT /books/999, then I get a 404 error."""
    response = client.put('/books/999', json={
        'title': 'Nonexistent',
        'author': 'Nobody'
    })
    assert response.status_code == 404


def test_delete_book(client):
    """Given a book exists, when I DELETE /books/{id}, then I get a 200 status."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    book_id = response.get_json()['id']

    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data


def test_delete_book_not_found(client):
    """Given a book doesn't exist, when I DELETE /books/999, then I get a 404 error."""
    response = client.delete('/books/999')
    assert response.status_code == 404


def test_delete_book_then_verify_gone(client):
    """Given a book exists, when I DELETE it, then GET returns 404."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    book_id = response.get_json()['id']

    client.delete(f'/books/{book_id}')
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404


def test_list_books_empty(client):
    """Given no books exist, when I GET /books, then I get an empty list."""
    response = client.get('/books')
    assert response.status_code == 200
    data = response.get_json()
    assert data == []


def test_create_book_empty_title(client):
    """Given a POST request with empty title, when I create a book, then I get a 400 error."""
    response = client.post('/books', json={
        'title': '',
        'author': 'Some Author'
    })
    assert response.status_code == 400


def test_create_book_invalid_year(client):
    """Given a POST request with invalid year, when I create a book, then I get a 400 error."""
    response = client.post('/books', json={
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 'not a number'
    })
    assert response.status_code == 400
