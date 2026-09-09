import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'books.db')})


@pytest.fixture
def client(app):
    return app.test_client()


def test_crud(client):
    data = {'title': 'Dune', 'author': 'Frank Herbert', 'year': 1965, 'isbn': '9780441172719'}
    response = client.post('/books', json=data)
    assert response.status_code == 201
    saved = response.get_json()
    assert saved == dict(data, id=saved['id'])
    path = response.headers['Location']
    assert client.get(path).get_json() == saved
    assert client.get('/books').get_json() == [saved]
    replacement = {'title': 'Dune Messiah', 'author': 'Frank Herbert'}
    response = client.put(path, json=replacement)
    assert response.status_code == 200
    assert response.get_json() == dict(replacement, id=saved['id'], year=None, isbn=None)
    assert client.get(path).get_json() == response.get_json()
    assert client.delete(path).status_code == 200
    assert client.get(path).status_code == 404
    assert client.get('/books').get_json() == []


def test_author_filter(client):
    for author in ['Alice', 'Bob', 'Alice']:
        assert client.post('/books', json={'title': 'Book', 'author': author}).status_code == 201
    rows = client.get('/books?author=Alice').get_json()
    assert len(rows) == 2
    assert all(row['author'] == 'Alice' for row in rows)
    assert client.get('/books?author=alice').get_json() == []
    assert client.get('/books', query_string={'author': "' OR 1=1 --"}).get_json() == []


@pytest.mark.parametrize('data', [
    {}, {'title': 'Book'}, {'author': 'Author'}, {'title': ' ', 'author': 'A'},
    {'title': 'T', 'author': 7}, [], 'text',
    {'title': 'T', 'author': 'A', 'year': True},
    {'title': 'T', 'author': 'A', 'year': '2000'},
    {'title': 'T', 'author': 'A', 'year': 0},
    {'title': 'T', 'author': 'A', 'year': 10000},
    {'title': 'T', 'author': 'A', 'isbn': 123},
    {'title': 'T', 'author': 'A', 'isbn': ' '},
    {'title': 'T', 'author': 'A', 'id': 12},
])
def test_validation(client, data):
    assert client.post('/books', json=data).status_code == 400
    assert client.get('/books').get_json() == []


def test_invalid_update_preserves_record(client):
    created = client.post('/books', json={'title': 'T', 'author': 'A'}).get_json()
    path = f"/books/{created['id']}"
    assert client.put(path, json={'title': ''}).status_code == 400
    assert client.get(path).get_json() == created


def test_missing_records_and_json_errors(client):
    for method in ('get', 'put', 'delete'):
        kwargs = {'json': {'title': 'T', 'author': 'A'}} if method == 'put' else {}
        response = getattr(client, method)('/books/999', **kwargs)
        assert response.status_code == 404
        assert 'error' in response.get_json()
    assert client.get('/unknown').is_json
    response = client.patch('/books/1')
    assert response.status_code == 405
    assert response.is_json
    assert 'Allow' in response.headers


def test_bad_json_and_content_type(client):
    assert client.post('/books', data='{', content_type='application/json').status_code == 400
    assert client.post('/books', data='text').status_code == 415
    assert client.post('/books', data='null', content_type='application/json').status_code == 400


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}


def test_persistence(app, client):
    created = client.post('/books', json={'title': ' T ', 'author': ' A '}).get_json()
    assert created['title'] == 'T'
    assert created['author'] == 'A'
    second = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']})
    assert second.test_client().get('/books').get_json() == [created]


@pytest.mark.parametrize('book_id', [0, 2**63, 10**100])
@pytest.mark.parametrize('method', ['get', 'put', 'delete'])
def test_out_of_range_ids_return_json_404(client, book_id, method):
    kwargs = {'json': {'title': 'T', 'author': 'A'}} if method == 'put' else {}
    response = getattr(client, method)(f'/books/{book_id}', **kwargs)
    assert response.status_code == 404
    assert response.get_json() == {'error': 'Book not found.'}


def test_wsgi_entry_point(tmp_path):
    import os
    import subprocess
    import sys

    environment = dict(os.environ, BOOKS_DATABASE=str(tmp_path / 'entrypoint.db'))
    result = subprocess.run(
        [sys.executable, '-c',
         'from app import app; '
         'response = app.test_client().get("/health"); '
         'assert response.status_code == 200; '
         'assert response.get_json() == {"status": "ok"}'],
        env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / 'entrypoint.db').exists()


def test_updates_and_deletes_persist(app, client):
    created = client.post('/books', json={'title': 'T', 'author': 'A'}).get_json()
    path = f"/books/{created['id']}"
    updated = {'title': 'New', 'author': 'Other', 'year': 2020, 'isbn': '123'}
    assert client.put(path, json=updated).get_json() == dict(updated, id=created['id'])
    second = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE']}).test_client()
    assert second.get(path).get_json() == dict(updated, id=created['id'])
    assert second.delete(path).status_code == 200
    assert client.get(path).status_code == 404
