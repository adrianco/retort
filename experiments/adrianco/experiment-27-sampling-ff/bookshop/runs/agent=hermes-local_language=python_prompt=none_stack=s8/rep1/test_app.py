"""Unit and integration tests for the Book API REST Service."""

import pytest
import os
import sys
import tempfile
import json

# Ensure the app module can be imported from the parent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    # Create a temp file for the database so tests don't pollute production db
    import app as application_module

    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()

    original_db = application_module.DATABASE
    application_module.DATABASE = temp_db.name

    # Re-initialize the database with the temp path
    application_module.init_db()

    application_module.app.config['TESTING'] = True

    with application_module.app.test_client() as client:
        yield client

    # Cleanup
    os.unlink(temp_db.name)


def test_health_check(client):
    """Given the health endpoint exists, when I call GET /health, then it returns 200."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_create_book(client):
    """Given no books exist, when I POST a new book with valid data, then it returns 201."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'The Great Gatsby'
    assert data['author'] == 'F. Scott Fitzgerald'
    assert data['year'] == 1925
    assert data['isbn'] == '978-0743273565'
    assert data['id'] is not None


def test_create_book_missing_title(client):
    """Given a book creation request, when title is missing, then it returns 400."""
    response = client.post('/books', json={
        'author': 'Unknown Author',
        'year': 2020,
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_create_book_missing_author(client):
    """Given a book creation request, when author is missing, then it returns 400."""
    response = client.post('/books', json={
        'title': 'Some Book',
        'year': 2020,
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_list_books(client):
    """Given multiple books exist, when I GET /books, then it returns all of them."""
    # Create a few books first
    client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
    })
    client.post('/books', json={
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949,
    })

    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2


def test_list_books_by_author(client):
    """Given multiple books exist, when I GET /books?author=Orwell, then it returns only Orwell's books."""
    client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
    })
    client.post('/books', json={
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949,
    })

    response = client.get('/books?author=Orwell')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['author'] == 'George Orwell'


def test_get_book_by_id(client):
    """Given a book exists, when I GET /books/{id}, then it returns the book."""
    response = client.post('/books', json={
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
    })
    book_id = json.loads(response.data)['id']

    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'To Kill a Mockingbird'


def test_get_book_not_found(client):
    """Given no book with that ID exists, when I GET /books/999, then it returns 404."""
    response = client.get('/books/999')
    assert response.status_code == 404


def test_update_book(client):
    """Given a book exists, when I PUT updated data, then it returns the updated book."""
    response = client.post('/books', json={
        'title': 'Original Title',
        'author': 'Author Name',
        'year': 2000,
    })
    book_id = json.loads(response.data)['id']

    response = client.put(f'/books/{book_id}', json={
        'title': 'Updated Title',
        'author': 'Author Name',
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'


def test_delete_book(client):
    """Given a book exists, when I DELETE /books/{id}, then it returns 200 and the book is gone."""
    response = client.post('/books', json={
        'title': 'Book to Delete',
        'author': 'Author Name',
    })
    book_id = json.loads(response.data)['id']

    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200

    # Verify the book is actually deleted
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404


def test_duplicate_isbn(client):
    """Given a book with an ISBN exists, when I POST another with the same ISBN, then it returns 409."""
    client.post('/books', json={
        'title': 'Book One',
        'author': 'Author One',
        'isbn': '123-456',
    })

    response = client.post('/books', json={
        'title': 'Book Two',
        'author': 'Author Two',
        'isbn': '123-456',
    })
    assert response.status_code == 409


def test_delete_book_not_found(client):
    """Given no book with that ID exists, when I DELETE /books/999, then it returns 404."""
    response = client.delete('/books/999')
    assert response.status_code == 404


def test_update_book_not_found(client):
    """Given no book with that ID exists, when I PUT /books/999, then it returns 404."""
    response = client.put('/books/999', json={
        'title': 'Non-existent Book',
        'author': 'Nobody',
    })
    assert response.status_code == 404


def test_create_book_no_json(client):
    """Given a POST request with no JSON body, when I create a book, then it returns 400."""
    response = client.post('/books', data='not json')
    assert response.status_code == 400


def test_invalid_year(client):
    """Given a book creation request with invalid year, when I POST, then it returns 400."""
    response = client.post('/books', json={
        'title': 'Bad Year Book',
        'author': 'Author Name',
        'year': 'not a number',
    })
    assert response.status_code == 400


def test_year_out_of_range(client):
    """Given a book creation request with year out of range, when I POST, then it returns 400."""
    response = client.post('/books', json={
        'title': 'Far Future Book',
        'author': 'Author Name',
        'year': 3000,
    })
    assert response.status_code == 400


def test_empty_request_body(client):
    """Given an empty JSON object, when I POST a book, then it returns 400."""
    response = client.post('/books', json={})
    assert response.status_code == 400


def test_list_books_empty(client):
    """Given no books exist, when I GET /books, then it returns an empty list."""
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 0


def test_partial_update(client):
    """Given a book exists, when I PUT only some fields, then it returns the updated book with other fields preserved."""
    response = client.post('/books', json={
        'title': 'Original Title',
        'author': 'Author Name',
        'year': 2000,
        'isbn': '111-222',
    })
    book_id = json.loads(response.data)['id']

    response = client.put(f'/books/{book_id}', json={
        'title': 'New Title',
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'New Title'
    # Other fields should remain unchanged
    assert data['author'] == 'Author Name'
    assert data['year'] == 2000


def test_author_filter_partial_match(client):
    """Given books with similar author names, when I filter by partial name, then it returns matching results."""
    client.post('/books', json={
        'title': 'Book A',
        'author': 'John Smith',
    })
    client.post('/books', json={
        'title': 'Book B',
        'author': 'Jane Smith',
    })
    client.post('/books', json={
        'title': 'Book C',
        'author': 'John Doe',
    })

    response = client.get('/books?author=John')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
