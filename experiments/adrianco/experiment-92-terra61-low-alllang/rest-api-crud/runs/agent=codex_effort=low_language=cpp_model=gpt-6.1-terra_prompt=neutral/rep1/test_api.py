import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest

BINARY = os.path.abspath(sys.argv.pop(1))

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, 'books.db')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.start_server()

    def start_server(self):
        self.proc = subprocess.Popen([BINARY, str(self.port), self.db], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=.1):
                    return
            except OSError:
                if self.proc.poll() is not None:
                    self.fail('Server failed to start: ' + self.proc.stderr.read().decode())
                time.sleep(.02)
        self.fail('Server did not start')

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait(timeout=5)
        self.proc.stderr.close()
        self.tmp.cleanup()

    def request(self, method, path, data=None, raw=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        body = raw if raw is not None else (json.dumps(data) if data is not None else None)
        conn.request(method, path, body, {'Content-Type': 'application/json'})
        res = conn.getresponse()
        result = (res.status, json.loads(res.read()))
        conn.close()
        return result

    def test_lifecycle_and_filter(self):
        self.assertEqual(self.request('GET', '/health'), (200, {'status': 'ok'}))
        status, book = self.request('POST', '/books', {'title': 'Dune', 'author': 'Herbert', 'year': 1965, 'isbn': '123'})
        self.assertEqual(status, 201)
        bid = book['id']
        self.request('POST', '/books', {'title': 'Other', 'author': 'Other'})
        self.assertEqual(self.request('GET', '/books?author=Herbert'), (200, [book]))
        self.assertEqual(self.request('GET', f'/books/{bid}'), (200, book))
        status, updated = self.request('PUT', f'/books/{bid}', {'title': 'Dune Messiah', 'author': 'Herbert'})
        self.assertEqual(status, 200)
        self.assertEqual(updated['title'], 'Dune Messiah')
        self.assertIsNone(updated['year'])
        self.assertEqual(self.request('DELETE', f'/books/{bid}')[0], 200)
        self.assertEqual(self.request('GET', f'/books/{bid}')[0], 404)
        self.assertEqual(self.request('DELETE', f'/books/{bid}')[0], 404)

    def test_validation_and_missing_routes(self):
        for payload in ({}, {'title': ' ', 'author': 'A'}, {'title': 'T', 'author': 1}, {'title': 'T', 'author': 'A', 'year': '2000'}, {'title': 'T', 'author': 'A', 'isbn': 123}):
            self.assertEqual(self.request('POST', '/books', payload)[0], 400)
        self.assertEqual(self.request('POST', '/books', raw='{broken')[0], 400)
        self.assertEqual(self.request('POST', '/books', raw='{} trailing')[0], 400)
        self.assertEqual(self.request('GET', '/books/0')[0], 404)
        self.assertEqual(self.request('PUT', '/books/999', {'title': 'T', 'author': 'A'})[0], 404)
        self.assertEqual(self.request('POST', '/books/1')[0], 405)
        self.assertEqual(self.request('GET', '/books')[1], [])

    def test_persistence(self):
        status, book = self.request('POST', '/books', {'title': 'Persistent', 'author': 'Author'})
        self.assertEqual(status, 201)
        self.proc.terminate()
        self.proc.wait(timeout=5)
        self.proc.stderr.close()
        self.start_server()
        self.assertEqual(self.request('GET', '/books'), (200, [book]))

if __name__ == '__main__':
    unittest.main()
