import tempfile
import unittest
from pathlib import Path

from app import create_app


class BookAPITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'books.db'
        self.app = create_app(self.database)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.book = {'title': 'A Book', 'author': 'An Author', 'year': 2020, 'isbn': '0012345678'}

    def test_crud(self):
        response = self.client.post('/books', json=self.book)
        self.assertEqual(response.status_code, 201)
        book = response.get_json()
        self.assertEqual(book, dict(self.book, id=1))
        location = response.headers['Location']
        self.assertEqual(self.client.get(location).get_json(), book)
        self.assertEqual(self.client.get('/books').get_json(), [book])
        response = self.client.put(location, json={'title': 'Revised', 'author': 'New Author'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), dict(id=1, title='Revised', author='New Author', year=None, isbn=None))
        self.assertEqual(self.client.get(location).get_json(), response.get_json())
        response = self.client.delete(location)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'id': 1, 'deleted': True})
        self.assertEqual(self.client.get(location).status_code, 404)
        self.assertEqual(self.client.get('/books').get_json(), [])

    def test_author_filter(self):
        self.client.post('/books', json=self.book)
        self.client.post('/books', json=dict(self.book, author='Someone Else'))
        result = self.client.get('/books', query_string={'author': 'An Author'}).get_json()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['author'], 'An Author')
        self.assertEqual(self.client.get('/books', query_string={'author': "' OR 1=1 --"}).get_json(), [])

    def test_validation(self):
        invalid = [{}, [], {'title': 'Only title'}, dict(self.book, author=' '),
                   dict(self.book, title=3), dict(self.book, year=True),
                   dict(self.book, year='2020'), dict(self.book, year=10000),
                   dict(self.book, isbn=123), dict(self.book, unexpected='value')]
        for payload in invalid:
            with self.subTest(payload=payload):
                response = self.client.post('/books', json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.get_json())
        self.assertEqual(self.client.get('/books').get_json(), [])
        self.client.post('/books', json=self.book)
        self.assertEqual(self.client.put('/books/1', json={}).status_code, 400)
        self.assertEqual(self.client.get('/books/1').get_json()['title'], self.book['title'])

    def test_json_errors_and_missing_books(self):
        self.assertEqual(self.client.post('/books', data='{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/books', data='text').status_code, 415)
        for method in ('get', 'put', 'delete'):
            response = getattr(self.client, method)('/books/999')
            self.assertEqual(response.status_code, 404)
            self.assertIn('error', response.get_json())
        self.assertEqual(self.client.patch('/books').status_code, 405)
        self.assertTrue(self.client.get('/unknown').is_json)

    def test_health_and_persistence(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})
        self.client.post('/books', json=self.book)
        other_client = create_app(self.database).test_client()
        self.assertEqual(other_client.get('/books/1').get_json(), dict(self.book, id=1))

    def test_update_all_fields_and_persist_deletion(self):
        response = self.client.post('/books', json=self.book)
        location = response.headers['Location']
        replacement = {'title': 'Another Book', 'author': 'Another Author',
                       'year': 2025, 'isbn': '9780000000002'}
        response = self.client.put(location, json=replacement)
        self.assertEqual(response.status_code, 200)
        expected = dict(replacement, id=1)
        self.assertEqual(response.get_json(), expected)
        other_client = create_app(self.database).test_client()
        self.assertEqual(other_client.get(location).get_json(), expected)
        self.assertEqual(other_client.get('/books', query_string={
            'author': self.book['author']}).get_json(), [])
        self.assertEqual(other_client.get('/books', query_string={
            'author': replacement['author']}).get_json(), [expected])
        self.assertEqual(other_client.delete(location).status_code, 200)
        restarted_client = create_app(self.database).test_client()
        self.assertEqual(restarted_client.get(location).status_code, 404)
        self.assertEqual(restarted_client.get('/books').get_json(), [])
        self.assertEqual(restarted_client.delete(location).status_code, 404)

    def test_required_fields_on_create_and_update(self):
        self.client.post('/books', json=self.book)
        for field in ('title', 'author'):
            for value in (None, '', '  ', 123, False):
                for method, path in (('post', '/books'), ('put', '/books/1')):
                    with self.subTest(field=field, value=value, method=method):
                        response = getattr(self.client, method)(
                            path, json=dict(self.book, **{field: value}))
                        self.assertEqual(response.status_code, 400)
                        self.assertIn('error', response.get_json())
            payload = dict(self.book)
            del payload[field]
            for method, path in (('post', '/books'), ('put', '/books/1')):
                with self.subTest(missing=field, method=method):
                    response = getattr(self.client, method)(path, json=payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('error', response.get_json())
        self.assertEqual(self.client.get('/books').get_json(), [dict(self.book, id=1)])

    def test_optional_fields_and_string_normalization(self):
        response = self.client.post('/books', json={
            'title': '  A Book  ', 'author': '  An Author  '})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {
            'id': 1, 'title': 'A Book', 'author': 'An Author',
            'year': None, 'isbn': None})


if __name__ == '__main__':
    unittest.main()
