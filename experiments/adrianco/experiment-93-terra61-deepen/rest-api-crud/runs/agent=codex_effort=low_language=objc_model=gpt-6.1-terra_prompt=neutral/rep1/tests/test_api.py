import http.client
import json
import os
import socket
import subprocess
import tempfile
import time
import unittest


class APITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.temp.name, 'test.sqlite3')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def request(self, method, path, body=None):
        client, server = socket.socketpair()
        proc = subprocess.Popen(['./test-harness', self.db, str(server.fileno())], pass_fds=(server.fileno(),))
        server.close()
        payload = b'' if body is None else json.dumps(body).encode()
        client.sendall(f'{method} {path} HTTP/1.1\r\nContent-Length: {len(payload)}\r\n\r\n'.encode() + payload)
        client.shutdown(socket.SHUT_WR)
        response = http.client.HTTPResponse(client)
        response.begin()
        data = response.read()
        status = response.status
        client.close()
        self.assertEqual(proc.wait(timeout=3), 0)
        return status, json.loads(data) if data else None

    def test_health(self):
        self.assertEqual(self.request('GET', '/health'), (200, {'status': 'ok'}))

    def test_crud_and_filter(self):
        status, book = self.request('POST', '/books', {'title': 'A', 'author': 'Test Author', 'year': 2020, 'isbn': '123'})
        self.assertEqual(status, 201)
        path = '/books/' + str(book['id'])
        self.assertEqual(self.request('GET', path), (200, book))
        self.assertIn(book, self.request('GET', '/books?author=Test%20Author')[1])
        self.assertEqual(self.request('GET', '/books?author=Nobody')[1], [])
        status, updated = self.request('PUT', path, {'title': 'B', 'author': 'Other'})
        self.assertEqual((status, updated['title'], updated['year']), (200, 'B', None))
        self.assertEqual(self.request('DELETE', path), (204, None))
        self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('DELETE', path)[0], 404)

    def test_validation_and_missing(self):
        for body in ({}, {'title': ' ', 'author': 'A'}, {'title': 'A', 'author': 'B', 'year': True}, {'title': 'A', 'author': 'B', 'isbn': 42}):
            self.assertEqual(self.request('POST', '/books', body)[0], 400)
        self.assertEqual(self.request('PUT', '/books/999999', {'title': 'A', 'author': 'B'})[0], 404)
        self.assertEqual(self.request('GET', '/books/nope')[0], 404)
        self.assertEqual(self.request('PATCH', '/books')[0], 405)

if __name__ == '__main__':
    unittest.main()
