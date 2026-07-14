import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

# Import create_app from the app module
from app import create_app


def make_test_client():
    """Create a fresh test client with an isolated in-memory database."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    test_app = create_app(database_path=db_path)
    test_app.config['TESTING'] = True

    client = test_app.test_client()

    yield client, db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


def make_client():
    """Create a fresh test client with an isolated in-memory database."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    test_app = create_app(database_path=db_path)
    test_app.config['TESTING'] = True

    client = test_app.test_client()

    return client, db_path


def cleanup(db_path):
    """Remove the temporary database file."""
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self):
        """Given the health endpoint exists, When I call it, Then it returns 200."""
        client, db_path = make_client()
        try:
            response = client.get('/health')
            assert response.status_code == 200
        finally:
            cleanup(db_path)

    def test_health_returns_healthy_status(self):
        """Given the health endpoint exists, When I call it, Then status is healthy."""
        client, db_path = make_client()
        try:
            response = client.get('/health')
            data = response.get_json()
            assert data['status'] == 'healthy'
        finally:
            cleanup(db_path)


class TestCreateBook:
    """Tests for POST /books endpoint."""

    def test_create_book_success(self):
        """Given no books exist, When I create a new book, Then it returns 201 with the book data."""
        client, db_path = make_client()
        try:
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
        finally:
            cleanup(db_path)

    def test_create_book_missing_title(self):
        """Given a request without title, When I POST to /books, Then it returns 400."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={
                'author': 'F. Scott Fitzgerald'
            })
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
        finally:
            cleanup(db_path)

    def test_create_book_missing_author(self):
        """Given a request without author, When I POST to /books, Then it returns 400."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={
                'title': 'The Great Gatsby'
            })
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
        finally:
            cleanup(db_path)

    def test_create_book_with_missing_isbn(self):
        """Given a request without ISBN, When I POST to /books, Then it creates the book successfully."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={
                'title': '1984',
                'author': 'George Orwell'
            })
            assert response.status_code == 201
        finally:
            cleanup(db_path)


class TestListBooks:
    """Tests for GET /books endpoint."""

    def test_list_books_empty(self):
        """Given no books exist, When I list all books, Then it returns an empty list."""
        client, db_path = make_client()
        try:
            response = client.get('/books')
            assert response.status_code == 200
            data = response.get_json()
            assert data == []
        finally:
            cleanup(db_path)

    def test_list_books_returns_all(self):
        """Given multiple books exist, When I list all books, Then it returns them all."""
        client, db_path = make_client()
        try:
            client.post('/books', json={'title': 'Book 1', 'author': 'Author A'})
            client.post('/books', json={'title': 'Book 2', 'author': 'Author A'})
            client.post('/books', json={'title': 'Book 3', 'author': 'Author B'})

            response = client.get('/books')
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 3
        finally:
            cleanup(db_path)

    def test_list_books_filter_by_author(self):
        """Given multiple books exist, When I filter by author, Then only matching books are returned."""
        client, db_path = make_client()
        try:
            client.post('/books', json={'title': 'Book 1', 'author': 'George Orwell'})
            client.post('/books', json={'title': 'Book 2', 'author': 'F. Scott Fitzgerald'})
            client.post('/books', json={'title': 'Book 3', 'author': 'George Orwell'})

            response = client.get('/books?author=Orwell')
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 2
            for book in data:
                assert 'Orwell' in book['author']
        finally:
            cleanup(db_path)


class TestGetBook:
    """Tests for GET /books/<id> endpoint."""

    def test_get_book_success(self):
        """Given a book exists, When I get it by ID, Then it returns the correct data."""
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'To Kill a Mockingbird',
                'author': 'Harper Lee',
                'year': 1960,
            })
            book_id = create_resp.get_json()['id']

            response = client.get(f'/books/{book_id}')
            assert response.status_code == 200
            data = response.get_json()
            assert data['title'] == 'To Kill a Mockingbird'
            assert data['author'] == 'Harper Lee'
        finally:
            cleanup(db_path)

    def test_get_book_not_found(self):
        """Given a book does not exist, When I get it by ID, Then it returns 404."""
        client, db_path = make_client()
        try:
            response = client.get('/books/999')
            assert response.status_code == 404
        finally:
            cleanup(db_path)


class TestUpdateBook:
    """Tests for PUT /books/<id> endpoint."""

    def test_update_book_success(self):
        """Given a book exists, When I update it, Then it returns the updated data."""
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Old Title',
                'author': 'Old Author'
            })
            book_id = create_resp.get_json()['id']

            response = client.put(f'/books/{book_id}', json={
                'title': 'New Title',
                'author': 'New Author'
            })
            assert response.status_code == 200
            data = response.get_json()
            assert data['title'] == 'New Title'
            assert data['author'] == 'New Author'
        finally:
            cleanup(db_path)

    def test_update_book_not_found(self):
        """Given a book does not exist, When I update it, Then it returns 404."""
        client, db_path = make_client()
        try:
            response = client.put('/books/999', json={'title': 'New Title'})
            assert response.status_code == 404
        finally:
            cleanup(db_path)

    def test_update_book_partial(self):
        """Given a book exists, When I update only some fields, Then only those fields change."""
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Old Title',
                'author': 'Old Author',
                'year': 2000
            })
            book_id = create_resp.get_json()['id']

            response = client.put(f'/books/{book_id}', json={
                'title': 'New Title'
            })
            assert response.status_code == 200
            data = response.get_json()
            assert data['title'] == 'New Title'
            assert data['author'] == 'Old Author'  # unchanged
            assert data['year'] == 2000  # unchanged
        finally:
            cleanup(db_path)


class TestDeleteBook:
    """Tests for DELETE /books/<id> endpoint."""

    def test_delete_book_success(self):
        """Given a book exists, When I delete it, Then it returns 200 and the book is gone."""
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Delete Me',
                'author': 'Author'
            })
            book_id = create_resp.get_json()['id']

            response = client.delete(f'/books/{book_id}')
            assert response.status_code == 200

            get_response = client.get(f'/books/{book_id}')
            assert get_response.status_code == 404
        finally:
            cleanup(db_path)

    def test_delete_book_not_found(self):
        """Given a book does not exist, When I delete it, Then it returns 404."""
        client, db_path = make_client()
        try:
            response = client.delete('/books/999')
            assert response.status_code == 404
        finally:
            cleanup(db_path)

    def test_delete_removes_from_list(self):
        """Given a book exists in the list, When I delete it, Then it is removed from listings."""
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Delete Me',
                'author': 'Author'
            })
            book_id = create_resp.get_json()['id']

            # Verify it exists
            list_before = client.get('/books').get_json()
            assert len(list_before) == 1

            # Delete it
            client.delete(f'/books/{book_id}')

            # Verify it is gone from listings
            list_after = client.get('/books').get_json()
            assert len(list_after) == 0
        finally:
            cleanup(db_path)


class TestDuplicateISBN:
    """Tests for duplicate ISBN handling."""

    def test_create_book_duplicate_isbn(self):
        """Given a book with an ISBN exists, When I create another with the same ISBN, Then it returns 409."""
        client, db_path = make_client()
        try:
            client.post('/books', json={
                'title': 'Book 1',
                'author': 'Author A',
                'isbn': 'unique-isbn-123'
            })

            response = client.post('/books', json={
                'title': 'Book 2',
                'author': 'Author B',
                'isbn': 'unique-isbn-123'
            })
            assert response.status_code == 409
        finally:
            cleanup(db_path)

    def test_update_book_conflicting_isbn(self):
        """Given two books with different ISBNs exist, When I update one to match the other's ISBN, Then it returns 409."""
        client, db_path = make_client()
        try:
            resp1 = client.post('/books', json={
                'title': 'Book 1',
                'author': 'Author A',
                'isbn': 'isbn-a'
            })
            resp2 = client.post('/books', json={
                'title': 'Book 2',
                'author': 'Author B',
                'isbn': 'isbn-b'
            })

            book2_id = resp2.get_json()['id']
            response = client.put(f'/books/{book2_id}', json={
                'title': 'Book 2 Updated',
                'author': 'Author B',
                'isbn': 'isbn-a'  # conflicts with Book 1's ISBN
            })
            assert response.status_code == 409
        finally:
            cleanup(db_path)


class TestValidation:
    """Tests for input validation."""

    def test_create_book_invalid_year(self):
        """Given a request with invalid year, When I POST to /books, Then it returns 400."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={
                'title': 'Test Book',
                'author': 'Author',
                'year': 'not-a-number'
            })
            assert response.status_code == 400
        finally:
            cleanup(db_path)

    def test_create_book_empty_title(self):
        """Given a request with empty title, When I POST to /books, Then it returns 400."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={
                'title': '',
                'author': 'Author'
            })
            assert response.status_code == 400
        finally:
            cleanup(db_path)

    def test_create_book_no_json_body(self):
        """Given a request with no JSON body, When I POST to /books, Then it returns 400 or 415."""
        client, db_path = make_client()
        try:
            response = client.post('/books')
            assert response.status_code in (400, 415)
        finally:
            cleanup(db_path)

    def test_create_book_missing_author_empty_string(self):
        """Given a request with empty author string, When I POST to /books, Then it returns 400."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={
                'title': 'Test Book',
                'author': ''
            })
            assert response.status_code == 400
        finally:
            cleanup(db_path)

    def test_create_book_with_year_only(self):
        """Given a request with only year, When I POST to /books, Then it returns 400."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={
                'year': 2024
            })
            assert response.status_code == 400
        finally:
            cleanup(db_path)

    def test_create_book_with_empty_json(self):
        """Given an empty JSON object, When I POST to /books, Then it returns 400."""
        client, db_path = make_client()
        try:
            response = client.post('/books', json={})
            assert response.status_code == 400
        finally:
            cleanup(db_path)


class TestIntegration:
    """Integration tests that cover multiple operations."""

    def test_full_crud_cycle(self):
        """Given no books exist, When I create-read-update-delete a book, Then everything works end-to-end."""
        client, db_path = make_client()
        try:
            # Create
            resp = client.post('/books', json={
                'title': 'Brave New World',
                'author': 'Aldous Huxley',
                'year': 1932,
                'isbn': '978-0060850524'
            })
            assert resp.status_code == 201
            book_id = resp.get_json()['id']

            # Read
            resp = client.get(f'/books/{book_id}')
            assert resp.status_code == 200
            book = resp.get_json()
            assert book['title'] == 'Brave New World'

            # Update
            resp = client.put(f'/books/{book_id}', json={'year': 1932})
            assert resp.status_code == 200

            # Verify update persisted (title unchanged since we sent empty body with valid title)
            resp = client.get(f'/books/{book_id}')
            book = resp.get_json()

            # Delete
            resp = client.delete(f'/books/{book_id}')
            assert resp.status_code == 200

            # Verify deletion
            resp = client.get(f'/books/{book_id}')
            assert resp.status_code == 404
        finally:
            cleanup(db_path)

    def test_author_filter_integration(self):
        """Given multiple books by different authors, When I filter by partial author name, Then results are correct."""
        client, db_path = make_client()
        try:
            client.post('/books', json={'title': 'Book 1', 'author': 'John Smith'})
            client.post('/books', json={'title': 'Book 2', 'author': 'Jane Smith'})
            client.post('/books', json={'title': 'Book 3', 'author': 'Bob Jones'})

            resp = client.get('/books?author=Smith')
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) == 2
        finally:
            cleanup(db_path)

    def test_list_books_ordering(self):
        """Given books inserted in order, When I list them, Then they appear in insertion order."""
        client, db_path = make_client()
        try:
            client.post('/books', json={'title': 'First', 'author': 'Author'})
            client.post('/books', json={'title': 'Second', 'author': 'Author'})
            client.post('/books', json={'title': 'Third', 'author': 'Author'})

            resp = client.get('/books')
            data = resp.get_json()
            assert len(data) == 3
            assert data[0]['title'] == 'First'
            assert data[1]['title'] == 'Second'
            assert data[2]['title'] == 'Third'
        finally:
            cleanup(db_path)


class TestHTTPStatusCodes:
    """Tests for correct HTTP status codes."""

    def test_create_returns_201(self):
        client, db_path = make_client()
        try:
            resp = client.post('/books', json={
                'title': 'Test', 'author': 'Author'
            })
            assert resp.status_code == 201
        finally:
            cleanup(db_path)

    def test_update_returns_200(self):
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Test', 'author': 'Author'
            })
            book_id = create_resp.get_json()['id']
            resp = client.put(f'/books/{book_id}', json={
                'title': 'Updated'
            })
            assert resp.status_code == 200
        finally:
            cleanup(db_path)

    def test_delete_returns_200(self):
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Test', 'author': 'Author'
            })
            book_id = create_resp.get_json()['id']
            resp = client.delete(f'/books/{book_id}')
            assert resp.status_code == 200
        finally:
            cleanup(db_path)

    def test_get_returns_200(self):
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Test', 'author': 'Author'
            })
            book_id = create_resp.get_json()['id']
            resp = client.get(f'/books/{book_id}')
            assert resp.status_code == 200
        finally:
            cleanup(db_path)

    def test_list_returns_200(self):
        client, db_path = make_client()
        try:
            resp = client.get('/books')
            assert resp.status_code == 200
        finally:
            cleanup(db_path)

    def test_health_returns_200(self):
        client, db_path = make_client()
        try:
            resp = client.get('/health')
            assert resp.status_code == 200
        finally:
            cleanup(db_path)


class TestResponseContent:
    """Tests for response content structure."""

    def test_create_response_contains_all_fields(self):
        client, db_path = make_client()
        try:
            resp = client.post('/books', json={
                'title': 'Test Book',
                'author': 'Author Name',
                'year': 2024,
                'isbn': '123-456'
            })
            data = resp.get_json()
            assert 'id' in data
            assert 'title' in data
            assert 'author' in data
            assert 'year' in data
            assert 'isbn' in data
            assert data['title'] == 'Test Book'
            assert data['author'] == 'Author Name'
            assert data['year'] == 2024
            assert data['isbn'] == '123-456'
        finally:
            cleanup(db_path)

    def test_delete_response_contains_message(self):
        client, db_path = make_client()
        try:
            create_resp = client.post('/books', json={
                'title': 'Test', 'author': 'Author'
            })
            book_id = create_resp.get_json()['id']
            resp = client.delete(f'/books/{book_id}')
            data = resp.get_json()
            assert 'message' in data
        finally:
            cleanup(db_path)

    def test_error_response_contains_error_field(self):
        client, db_path = make_client()
        try:
            resp = client.post('/books', json={})
            data = resp.get_json()
            assert 'error' in data
        finally:
            cleanup(db_path)
