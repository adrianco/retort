import os
import pytest
import app


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    """Use a temporary database file for each test."""
    import sqlite3

    db_path = '/tmp/test_books_' + str(id(object())) + '.db'

    # Use setitem to override the config dict value
    monkeypatch.setitem(app.app.config, 'DATABASE', db_path)

    # Re-initialize the DB to clear stale data
    with app.app.app_context():
        conn = sqlite3.connect(db_path)
        conn.execute('DROP TABLE IF EXISTS books')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
        ''')
        conn.commit()
        conn.close()

    yield

    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestCreateBook:
    def test_create_book_success(self, client):
        data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = client.post('/books', json=data)
        assert response.status_code == 201
        result = response.get_json()
        assert result['title'] == 'The Great Gatsby'
        assert result['author'] == 'F. Scott Fitzgerald'
        assert result['year'] == 1925
        assert result['isbn'] == '978-0743273565'
        assert 'id' in result

    def test_create_book_missing_title(self, client):
        data = {
            'author': 'Unknown Author',
            'year': 2000
        }
        response = client.post('/books', json=data)
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_create_book_missing_author(self, client):
        data = {
            'title': 'Some Book',
            'year': 2000
        }
        response = client.post('/books', json=data)
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_create_book_no_body(self, client):
        response = client.post('/books', content_type='application/json')
        assert response.status_code in (400, 415)


class TestListBooks:
    def test_list_books_empty(self, client):
        response = client.get('/books')
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_books_with_data(self, client):
        client.post('/books', json={'title': 'Book 1', 'author': 'Author A', 'year': 2020, 'isbn': '111'})
        client.post('/books', json={'title': 'Book 2', 'author': 'Author B', 'year': 2021, 'isbn': '222'})
        response = client.get('/books')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        client.post('/books', json={'title': 'Book 1', 'author': 'Author A', 'year': 2020, 'isbn': '111'})
        client.post('/books', json={'title': 'Book 2', 'author': 'Author B', 'year': 2021, 'isbn': '222'})
        client.post('/books', json={'title': 'Book 3', 'author': 'Author A', 'year': 2022, 'isbn': '333'})
        response = client.get('/books?author=Author A')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert 'Author A' in book['author']


class TestGetBook:
    def test_get_book_not_found(self, client):
        response = client.get('/books/999')
        assert response.status_code == 404

    def test_get_book_success(self, client):
        create_resp = client.post('/books', json={'title': 'Book', 'author': 'Auth', 'year': 2020})
        book_id = create_resp.get_json()['id']
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Book'


class TestUpdateBook:
    def test_update_book_success(self, client):
        create_resp = client.post('/books', json={'title': 'Old Title', 'author': 'Auth', 'year': 2020})
        book_id = create_resp.get_json()['id']
        update_data = {'title': 'New Title', 'author': 'New Author', 'year': 2023, 'isbn': '444'}
        response = client.put(f'/books/{book_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'New Title'
        assert data['author'] == 'New Author'

    def test_update_book_not_found(self, client):
        response = client.put('/books/999', json={'title': 'X', 'author': 'Y'})
        assert response.status_code == 404

    def test_update_book_missing_title(self, client):
        create_resp = client.post('/books', json={'title': 'Old', 'author': 'Auth', 'year': 2020})
        book_id = create_resp.get_json()['id']
        response = client.put(f'/books/{book_id}', json={'author': 'New Auth'})
        assert response.status_code == 400


class TestDeleteBook:
    def test_delete_book_success(self, client):
        create_resp = client.post('/books', json={'title': 'Book', 'author': 'Auth', 'year': 2020})
        book_id = create_resp.get_json()['id']
        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        assert response.get_json()['message'] == 'Book deleted successfully'

    def test_delete_book_not_found(self, client):
        response = client.delete('/books/999')
        assert response.status_code == 404
