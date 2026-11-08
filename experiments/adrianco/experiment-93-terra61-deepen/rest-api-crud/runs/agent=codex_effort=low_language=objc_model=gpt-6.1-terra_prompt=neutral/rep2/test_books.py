import http.client
import json
import os
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.parse import quote


class BooksAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp.name, 'books.sqlite3')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def request(self, method, path, body=None):
        client, server = socket.socketpair()
        env = dict(os.environ, BOOKS_DB=self.db_path, BOOKS_TEST_FD=str(server.fileno()))
        process = subprocess.Popen(['./books'], env=env, pass_fds=(server.fileno(),),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        server.close()
        payload = json.dumps(body).encode() if body is not None else b''
        request = (f'{method} {path} HTTP/1.1\r\nHost: localhost\r\n'
                   f'Content-Length: {len(payload)}\r\nContent-Type: application/json\r\n\r\n').encode() + payload
        client.sendall(request)
        response = http.client.HTTPResponse(client)
        response.begin()
        result = json.loads(response.read())
        status = response.status
        client.close()
        _, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, stderr.decode())
        return status, result

    def test_health(self):
        self.assertEqual(self.request('GET', '/health'), (200, {'status': 'ok'}))

    def test_crud_and_filter(self):
        data = {'title': 'A Book', 'author': 'A & B', 'year': 2020, 'isbn': '123'}
        status, created = self.request('POST', '/books', data)
        self.assertEqual(status, 201)
        ident = created['id']
        self.assertEqual(self.request('GET', f'/books/{ident}'), (200, dict(data, id=ident)))
        status, found = self.request('GET', '/books?author=' + quote('A & B'))
        self.assertEqual(status, 200)
        self.assertIn(created, found)
        self.assertEqual(self.request('GET', '/books?author=Nobody'), (200, []))
        updated = {'title': 'New title', 'author': 'Another'}
        status, result = self.request('PUT', f'/books/{ident}', updated)
        self.assertEqual(status, 200)
        self.assertEqual(result, dict(updated, id=ident, year=None, isbn=None))
        self.assertEqual(self.request('GET', f'/books/{ident}'), (200, result))
        self.assertEqual(self.request('DELETE', f'/books/{ident}'), (200, {'deleted': ident}))
        self.assertEqual(self.request('GET', f'/books/{ident}')[0], 404)
        self.assertEqual(self.request('DELETE', f'/books/{ident}')[0], 404)
        self.assertEqual(self.request('PUT', f'/books/{ident}', updated)[0], 404)

    def test_validation(self):
        for payload in ({}, {'title': ' ', 'author': 'X'}, {'title': 'X', 'author': 'Y', 'year': True},
                        {'title': 'X', 'author': 'Y', 'year': 1.5}, {'title': 'X', 'author': 'Y', 'isbn': 12}, []):
            with self.subTest(payload=payload):
                self.assertEqual(self.request('POST', '/books', payload)[0], 400)
        self.assertEqual(self.request('GET', '/books/not-an-id')[0], 404)
        self.assertEqual(self.request('PATCH', '/books')[0], 405)

    def test_persistence(self):
        status, book = self.request('POST', '/books', {'title': 'Persistent', 'author': 'Writer'})
        self.assertEqual(status, 201)
        import sqlite3
        with sqlite3.connect(os.path.join(self.temp.name, 'books.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT title, author FROM books WHERE id=?', (book['id'],)).fetchone(), ('Persistent', 'Writer'))


if __name__ == '__main__':
    unittest.main()
