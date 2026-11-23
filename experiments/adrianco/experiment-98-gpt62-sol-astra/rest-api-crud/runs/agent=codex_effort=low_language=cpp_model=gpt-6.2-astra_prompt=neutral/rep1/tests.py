import socket
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SERVER = sys.argv.pop(1)


class BookAPI(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "books.db"

    def request(self, method, path, status, body=None):
        client, server = socket.socketpair()
        with server:
            proc = subprocess.Popen([SERVER, self.database, str(server.fileno())],
                                    pass_fds=(server.fileno(),))
        conn = http.client.HTTPConnection("localhost")
        client.settimeout(3)
        conn.sock = client
        try:
            payload = body if isinstance(body, str) else json.dumps(body) if body is not None else None
            conn.request(method, path, payload, {"Content-Type": "application/json"})
            response = conn.getresponse()
            data = json.load(response)
            self.assertEqual(response.status, status, data)
            self.assertEqual(response.getheader("Content-Type"), "application/json")
            return data
        finally:
            conn.close()
            self.assertEqual(proc.wait(timeout=5), 0)

    def test_crud(self):
        fields = dict(title="Kindred", author="Octavia Butler", year=1979, isbn="001")
        book = self.request("POST", "/books", 201, fields)
        self.assertEqual(book, dict(fields, id=book["id"]))
        path = f"/books/{book['id']}"
        self.assertEqual(self.request("GET", path, 200), book)
        updated = self.request("PUT", path, 200, dict(title="Dawn", author=fields["author"]))
        self.assertEqual(updated, dict(id=book["id"], title="Dawn", author=fields["author"], year=None, isbn=None))
        self.assertEqual(self.request("GET", path, 200), updated)
        self.request("DELETE", path, 200)
        for method in ["GET", "DELETE", "PUT"]:
            self.request(method, path, 404, fields if method == "PUT" else None)

    def test_list_filter_and_persistence(self):
        books = [self.request("POST", "/books", 201, dict(title="Stories", author=name))
                 for name in ["A & B", "C"]]
        self.assertEqual(self.request("GET", "/books", 200), books)
        self.assertEqual(self.request("GET", "/books?author=A+%26+B", 200), books[:1])
        self.assertEqual(self.request("GET", "/books?author=Unknown", 200), [])

    def test_validation(self):
        valid = dict(title="Stories", author="A")
        for invalid in ["{", [], {}, {"title": "T"}, {"author": "A"},
                        dict(valid, title=" "), dict(valid, year="1999"), dict(valid, isbn=1)]:
            with self.subTest(invalid=invalid):
                self.request("POST", "/books", 400, invalid)
        self.assertEqual(self.request("GET", "/books", 200), [])

    def test_health_and_routing(self):
        self.assertEqual(self.request("GET", "/health", 200), {"status": "ok"})
        self.request("GET", "/unknown", 404)
        self.request("PATCH", "/books", 405)


if __name__ == "__main__":
    unittest.main()
