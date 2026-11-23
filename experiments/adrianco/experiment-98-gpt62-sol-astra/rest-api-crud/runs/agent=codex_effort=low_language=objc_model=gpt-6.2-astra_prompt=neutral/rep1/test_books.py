import json
import os
import subprocess
import tempfile
import unittest


class BookAPI(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.env = dict(os.environ, BOOKS_DB=os.path.join(folder.name, "books.db"))
        self.book = dict(title="First", author="A & B", year=2020, isbn="001")

    def request(self, method, path, data=None, status=200):
        body = json.dumps(data).encode() if data is not None else b""
        headers = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n"
        raw = subprocess.check_output(["./books", "--stdio"], input=headers.encode()+body, env=self.env)
        head, payload = raw.split(b"\r\n\r\n", 1)
        self.assertEqual(int(head.split()[1]), status, payload)
        self.assertIn(b"Content-Type: application/json", head)
        return json.loads(payload)

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), {"status": "ok"})

    def test_lifecycle(self):
        created = self.request("POST", "/books", self.book, 201)
        path = f"/books/{created['id']}"
        self.assertEqual(created, dict(self.book, id=created["id"]))
        self.assertEqual(self.request("GET", path), created)
        updated = dict(self.book, title="Second")
        self.request("PUT", path, updated)
        self.assertEqual(self.request("GET", path), dict(updated, id=created["id"]))
        self.request("DELETE", path)
        for method in ("GET", "PUT", "DELETE"):
            self.request(method, path, updated, 404)

    def test_filter(self):
        first = self.request("POST", "/books", self.book, 201)
        second = self.request("POST", "/books", dict(title="Two", author="Other"), 201)
        self.assertEqual(self.request("GET", "/books"), [first, second])
        self.assertEqual(self.request("GET", "/books?author=A%20%26%20B"), [first])
        self.assertEqual(self.request("GET", "/books?author=absent"), [])

    def test_validation(self):
        for invalid in ({"author": "A"}, {"title": "T"}, dict(self.book, author="  "),
                        dict(self.book, year=True), dict(self.book, isbn=123)):
            self.request("POST", "/books", invalid, 400)
        self.assertEqual(self.request("GET", "/books"), [])
