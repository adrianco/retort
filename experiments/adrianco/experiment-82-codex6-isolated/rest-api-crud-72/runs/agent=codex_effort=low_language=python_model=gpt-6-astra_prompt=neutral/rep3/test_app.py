import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

from app import create_app


class BookAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / 'books.sqlite3'
        self.app = create_app(self.database)

    def request(self, method, path, data=None, raw=None, content_type='application/json'):
        body = raw if raw is not None else json.dumps(data).encode()
        environ = {}
        setup_testing_defaults(environ)
        path, _, query = path.partition('?')
        environ.update(REQUEST_METHOD=method, PATH_INFO=path, QUERY_STRING=query,
                       CONTENT_TYPE=content_type, CONTENT_LENGTH=str(len(body)),
                       **{'wsgi.input': io.BytesIO(body)})
        response = {}
        def start(status, headers):
            response.update(status=int(status.split()[0]), headers=dict(headers))
        body = b''.join(self.app(environ, start))
        response['data'] = json.loads(body) if body else None
        return response

    def create(self, **fields):
        return self.request('POST', '/books', {'title': 'Dune', 'author': 'Frank Herbert',
                                             'year': 1965, 'isbn': '9780441172719', **fields})

    def test_crud(self):
        created = self.create()
        self.assertEqual(created['status'], 201)
        path = created['headers']['Location']
        self.assertEqual(self.request('GET', path)['data'], created['data'])
        updated = self.request('PUT', path, {'title': 'New title', 'author': 'New author'})
        self.assertEqual(updated['status'], 200)
        self.assertEqual(updated['data']['title'], 'New title')
        self.assertIsNone(updated['data']['year'])
        self.assertIsNone(updated['data']['isbn'])
        self.assertEqual(self.request('GET', path)['data'], updated['data'])
        self.assertEqual(self.request('DELETE', path)['status'], 204)
        for method in ('GET', 'PUT', 'DELETE'):
            self.assertEqual(self.request(method, path)['status'], 404)

    def test_list_and_filter(self):
        self.assertEqual(self.request('GET', '/books')['data'], [])
        self.create()
        self.create(title='Another')
        self.create(author='Other')
        self.assertEqual(len(self.request('GET', '/books')['data']), 3)
        self.assertEqual(len(self.request('GET', '/books?author=Frank%20Herbert')['data']), 2)
        self.assertEqual(self.request('GET', '/books?author=%27%20OR%201=1--')['data'], [])

    def test_validation(self):
        invalid = [{}, [], None, {'title': 'A'}, {'author': 'A'},
                   {'title': '  ', 'author': 'A'}, {'title': 123, 'author': 'A'}]
        for data in invalid:
            with self.subTest(data=data):
                self.assertEqual(self.request('POST', '/books', data)['status'], 400)
        for fields in ({'year': True}, {'year': '1965'}, {'year': 0},
                       {'isbn': 123}, {'isbn': ''}, {'unexpected': 1}):
            with self.subTest(fields=fields):
                self.assertEqual(self.create(**fields)['status'], 400)
        self.assertEqual(self.request('GET', '/books')['data'], [])

    def test_invalid_update_preserves_book(self):
        book = self.create()
        path = book['headers']['Location']
        self.assertEqual(self.request('PUT', path, {'title': 'X'})['status'], 400)
        self.assertEqual(self.request('GET', path)['data'], book['data'])

    def test_json_and_http_errors(self):
        self.assertEqual(self.request('POST', '/books', raw=b'{')['status'], 400)
        self.assertEqual(self.request('POST', '/books', raw=b'\xff')['status'], 400)
        self.assertEqual(self.request('POST', '/books', content_type='text/plain')['status'], 415)
        self.assertEqual(self.request('POST', '/books', raw=b'x' * (1024 * 1024 + 1))['status'], 413)
        result = self.request('PATCH', '/books/1')
        self.assertEqual(result['status'], 405)
        self.assertEqual(result['headers']['Allow'], 'GET, PUT, DELETE')
        for path in ('/missing', '/books/nope', '/books/' + '9' * 100):
            self.assertEqual(self.request('GET', path)['status'], 404)

    def test_persistence(self):
        book = self.create()['data']
        self.app = create_app(self.database)
        self.assertEqual(self.request('GET', f'/books/{book["id"]}')['data'], book)

    def test_health(self):
        response = self.request('GET', '/health')
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['data'], {'status': 'ok'})

    def test_health_over_http(self):
        try:
            server = make_server('127.0.0.1', 0, self.app)
        except PermissionError:
            self.skipTest('Environment prohibits listening sockets')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(f'http://127.0.0.1:{server.server_port}/health', timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(json.load(response), {'status': 'ok'})
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
