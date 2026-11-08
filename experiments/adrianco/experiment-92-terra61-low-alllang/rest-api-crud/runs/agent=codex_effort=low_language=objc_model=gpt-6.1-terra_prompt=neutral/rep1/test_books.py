import json
import os
import socket
import subprocess
import tempfile
import unittest


class BooksAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, BOOKS_DB=os.path.join(self.tmp.name, 'books.db'))

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, method, path, body=None):
        client, server = socket.socketpair()
        payload = json.dumps(body).encode() if body is not None else b''
        env = dict(self.env, BOOKS_TEST_FD=str(server.fileno()))
        process = subprocess.Popen(['./books-server'], env=env, pass_fds=(server.fileno(),), stderr=subprocess.PIPE)
        server.close()
        client.sendall(f'{method} {path} HTTP/1.1\r\nContent-Length: {len(payload)}\r\n\r\n'.encode() + payload)
        chunks = []
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        client.close()
        _, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, stderr.decode())
        headers, response_body = b''.join(chunks).split(b'\r\n\r\n', 1)
        status = int(headers.split(b' ', 2)[1])
        return status, json.loads(response_body)

    def test_health_and_empty_list(self):
        self.assertEqual(self.request('GET', '/health'), (200, {'status': 'ok'}))
        self.assertEqual(self.request('GET', '/books'), (200, []))

    def test_crud_and_filter(self):
        status, first = self.request('POST', '/books', {'title': 'One', 'author': 'A B', 'year': 2001, 'isbn': '123'})
        self.assertEqual(status, 201)
        self.assertEqual(first['year'], 2001)
        _, second = self.request('POST', '/books', {'title': 'Two', 'author': 'Other'})
        self.assertEqual(self.request('GET', '/books?author=A%20B'), (200, [first]))
        self.assertEqual(self.request('GET', '/books/' + str(first['id'])), (200, first))
        status, updated = self.request('PUT', '/books/' + str(first['id']), {'title': 'Changed', 'author': 'Other'})
        self.assertEqual(status, 200)
        self.assertEqual(updated['title'], 'Changed')
        self.assertIsNone(updated['year'])
        self.assertEqual(len(self.request('GET', '/books?author=Other')[1]), 2)
        self.assertEqual(self.request('DELETE', '/books/' + str(second['id']))[0], 200)
        self.assertEqual(self.request('GET', '/books/' + str(second['id']))[0], 404)
        self.assertEqual(self.request('DELETE', '/books/' + str(second['id']))[0], 404)

    def test_validation_and_missing(self):
        for body in ({}, {'title': ' ', 'author': 'A'}, {'title': 'T', 'author': ''},
                     {'title': 'T', 'author': 'A', 'year': True},
                     {'title': 'T', 'author': 'A', 'isbn': 123}):
            self.assertEqual(self.request('POST', '/books', body)[0], 400)
        self.assertEqual(self.request('PUT', '/books/999', {'title': 'T', 'author': 'A'})[0], 404)
        self.assertEqual(self.request('GET', '/books/abc')[0], 404)
        self.assertEqual(self.request('POST', '/health')[0], 405)

    def test_persistence(self):
        _, book = self.request('POST', '/books', {'title': 'Persistent', 'author': 'A'})
        self.assertEqual(self.request('GET', '/books/' + str(book['id'])), (200, book))


if __name__ == '__main__':
    unittest.main()
