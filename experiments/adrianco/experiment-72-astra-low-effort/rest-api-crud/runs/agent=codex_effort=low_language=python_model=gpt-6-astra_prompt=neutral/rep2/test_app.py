import io
import json

import pytest

from app import create_app


@pytest.fixture
def api(tmp_path):
    return create_app(tmp_path / 'books.db')


def request(api, method, path, data=None, raw=None, content_type='application/json'):
    body = raw if raw is not None else json.dumps(data).encode()
    route, _, query = path.partition('?')
    env = {'REQUEST_METHOD': method, 'PATH_INFO': route, 'QUERY_STRING': query,
           'CONTENT_TYPE': content_type, 'CONTENT_LENGTH': str(len(body)),
           'wsgi.input': io.BytesIO(body)}
    response = {}
    def start(status, headers):
        response.update(status=int(status.split()[0]), headers=dict(headers))
    response['body'] = json.loads(b''.join(api(env, start)))
    assert response['headers']['Content-Type'].startswith('application/json')
    return response


def test_crud(api):
    book = {'title': 'Dune', 'author': 'Frank Herbert', 'year': 1965, 'isbn': '9780441172719'}
    created = request(api, 'POST', '/books', book)
    assert created['status'] == 201
    path = created['headers']['Location']
    assert created['body'] == {'id': 1, **book}
    assert request(api, 'GET', path)['body'] == created['body']
    assert request(api, 'GET', '/books')['body'] == [created['body']]
    updated = request(api, 'PUT', path, {'title': 'New title', 'author': 'New author'})
    assert updated['status'] == 200
    assert updated['body'] == {'id': 1, 'title': 'New title', 'author': 'New author', 'year': None, 'isbn': None}
    assert request(api, 'GET', path)['body'] == updated['body']
    assert request(api, 'DELETE', path)['status'] == 200
    assert request(api, 'GET', path)['status'] == 404
    assert request(api, 'GET', '/books')['body'] == []


@pytest.mark.parametrize('data', [{}, {'title': 'x'}, {'title': '', 'author': 'x'},
    {'title': 'x', 'author': '  '}, {'title': 1, 'author': 'x'}, [],
    {'title': 'x', 'author': 'a', 'year': True}, {'title': 'x', 'author': 'a', 'year': '2000'},
    {'title': 'x', 'author': 'a', 'year': 2**64}, {'title': 'x', 'author': 'a', 'isbn': 123},
    {'title': 'x', 'author': 'a', 'id': 1}])
def test_validation(api, data):
    assert request(api, 'POST', '/books', data)['status'] == 400
    assert request(api, 'GET', '/books')['body'] == []


def test_filter_and_sql_safety(api):
    for author in ['Alice', 'Bob', "O'Reilly"]:
        request(api, 'POST', '/books', {'title': 'Book', 'author': author})
    assert len(request(api, 'GET', '/books?author=Alice')['body']) == 1
    assert request(api, 'GET', '/books?author=Missing')['body'] == []
    assert request(api, 'GET', '/books?author=')['body'] == []
    assert request(api, 'GET', '/books?author=O%27Reilly')['body'][0]['author'] == "O'Reilly"
    assert request(api, 'GET', '/books?author=%27+OR+1%3D1--')['body'] == []


def test_errors_and_health(api):
    assert request(api, 'GET', '/health')['body'] == {'status': 'ok'}
    for method in ['GET', 'PUT', 'DELETE']:
        assert request(api, method, '/books/999')['status'] == 404
    assert request(api, 'GET', '/unknown')['status'] == 404
    assert request(api, 'PATCH', '/books')['status'] == 405
    assert request(api, 'POST', '/books', raw=b'{')['status'] == 400
    assert request(api, 'POST', '/books', content_type='text/plain')['status'] == 415
    assert request(api, 'POST', '/books', raw=b'x' * 1_000_001)['status'] == 413


def test_persistence_and_failed_update(tmp_path):
    path = tmp_path / 'persistent.db'
    first = create_app(path)
    original = request(first, 'POST', '/books', {'title': ' Book ', 'author': ' Author '})['body']
    second = create_app(path)
    assert request(second, 'GET', '/books/1')['body'] == original
    assert request(second, 'PUT', '/books/1', {'title': 'bad'})['status'] == 400
    assert request(second, 'GET', '/books/1')['body'] == original
