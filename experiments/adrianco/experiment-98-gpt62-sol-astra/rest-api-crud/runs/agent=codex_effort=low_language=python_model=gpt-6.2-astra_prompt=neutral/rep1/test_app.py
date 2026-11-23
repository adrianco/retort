import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from app import create_app


class BooksTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "books.db"
        self.app = create_app(self.path)
        self.book = dict(title="Kindred", author="Octavia Butler", year=1979, isbn="0123")

    def request(self, method, url, data=None):
        path, _, query = url.partition("?")
        body = json.dumps(data).encode()
        env = dict(REQUEST_METHOD=method, PATH_INFO=path, QUERY_STRING=query,
                   CONTENT_TYPE="application/json", CONTENT_LENGTH=str(len(body)))
        env["wsgi.input"] = BytesIO(body)
        response = []
        payload = b"".join(self.app(env, lambda status, headers: response.extend([status, dict(headers)])))
        self.assertEqual(response[1]["Content-Type"], "application/json")
        return int(response[0].split()[0]), json.loads(payload)

    def test_lifecycle_and_persistence(self):
        status, created = self.request("POST", "/books", self.book)
        self.assertEqual(status, 201)
        url = f"/books/{created['id']}"
        self.app = create_app(self.path)
        self.assertEqual(self.request("GET", url), (200, dict(self.book, id=created["id"])))
        status, updated = self.request("PUT", url, dict(title="Dawn", author="Butler"))
        self.assertEqual((status, updated["title"], updated["year"]), (200, "Dawn", None))
        self.assertEqual(self.request("GET", url), (200, updated))
        self.assertEqual(self.request("DELETE", url)[0], 200)
        for method in ("GET", "PUT", "DELETE"):
            self.assertEqual(self.request(method, url, self.book)[0], 404)

    def test_listing(self):
        self.request("POST", "/books", self.book)
        self.request("POST", "/books", dict(title="Emma", author="Jane Austen"))
        self.assertEqual(len(self.request("GET", "/books")[1]), 2)
        status, books = self.request("GET", "/books?author=Jane+Austen")
        self.assertEqual((status, [b["title"] for b in books]), (200, ["Emma"]))

    def test_validation(self):
        for invalid in ({}, {"author": "A"}, {"title": "A"}, dict(self.book, title=" "),
                        dict(self.book, year=True), dict(self.book, isbn=123)):
            self.assertEqual(self.request("POST", "/books", invalid)[0], 400)
        self.assertEqual(self.request("GET", "/books"), (200, []))

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))
