import json
import os
import socket
import subprocess
import tempfile
import unittest
from urllib.parse import quote


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, 'books.db')

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, method, path, body=None):
        if isinstance(body, dict):
            body = json.dumps(body)
        data = (body or '').encode()
        request = (f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n"
                   f"Content-Length: {len(data)}\r\n\r\n").encode() + data
        parent, child = socket.socketpair()
        with parent, child:
            proc = subprocess.Popen(['./books-api'], pass_fds=(child.fileno(),),
                                    env={**os.environ, 'BOOKS_DB': self.db,
                                         'BOOKS_REQUEST_FD': str(child.fileno())},
                                    stderr=subprocess.PIPE)
            child.close()
            parent.sendall(request)
            parent.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = parent.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            stderr = proc.communicate(timeout=2)[1]
            self.assertEqual(proc.returncode, 0, stderr.decode())
        headers, response_body = b''.join(chunks).split(b'\r\n\r\n', 1)
        status = int(headers.split(b' ', 2)[1])
        return status, json.loads(response_body)

    def test_health(self):
        self.assertEqual(self.request('GET', '/health'), (200, {'status': 'ok'}))

    def test_crud_and_filter(self):
        status, book = self.request('POST', '/books', {'title': 'A', 'author': 'Ada Lovelace', 'year': 1843, 'isbn': '123'})
        self.assertEqual(status, 201)
        ident = book['id']
        self.assertEqual(self.request('GET', f'/books/{ident}'), (200, book))
        self.assertIn(book, self.request('GET', '/books?author=' + quote('Ada Lovelace'))[1])
        self.assertEqual(self.request('GET', '/books?author=Nobody')[1], [])
        status, updated = self.request('PUT', f'/books/{ident}', {'title': 'B', 'author': 'Grace'})
        self.assertEqual((status, updated['title'], updated['year']), (200, 'B', None))
        self.assertEqual(self.request('DELETE', f'/books/{ident}')[0], 200)
        self.assertEqual(self.request('GET', f'/books/{ident}')[0], 404)
        self.assertEqual(self.request('DELETE', f'/books/{ident}')[0], 404)

    def test_validation_and_missing(self):
        for body in ({}, {'title': ' ', 'author': 'A'}, {'title': 'T', 'author': 'A', 'year': 'bad'}, '{bad'):
            self.assertEqual(self.request('POST', '/books', body)[0], 400)
        self.assertEqual(self.request('PUT', '/books/999999', {'title': 'T', 'author': 'A'})[0], 404)
        self.assertEqual(self.request('GET', '/books/not-an-id')[0], 404)
        self.assertEqual(self.request('POST', '/health')[0], 405)

    def test_persistence(self):
        status, book = self.request('POST', '/books', {'title': 'Persistent', 'author': 'Writer'})
        self.assertEqual(status, 201)
        self.assertEqual(self.request('GET', f"/books/{book['id']}"), (200, book))


if __name__ == '__main__':
    unittest.main()
