import http.client
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.parse import urlencode


class BookApiTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.database = Path(directory) / "books.db"
        self.start()

    def start(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.server = subprocess.Popen([
            str(Path(__file__).resolve().with_name("book-api")),
            str(self.port), str(self.database),
        ])
        self.addCleanup(self.stop, self.server)
        for _ in range(100):
            if self.server.poll() is not None:
                self.fail(f"Server exited with status {self.server.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.02)
        self.fail("Server did not start")

    @staticmethod
    def stop(server):
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    def request(self, method, path, body=None, expected=200):
        if isinstance(body, dict):
            body = json.dumps(body)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body, {"Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read()
            self.assertEqual(response.status, expected, raw)
            if expected == 204:
                self.assertEqual(raw, b"")
                return None, response.headers
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return json.loads(raw), response.headers
        finally:
            connection.close()

    def create(self, **book):
        created, headers = self.request("POST", "/books", book, 201)
        self.assertEqual(headers["Location"], f"/books/{created['id']}")
        return created, headers["Location"]

    def test_health_and_empty_collection(self):
        self.assertEqual(self.request("GET", "/health")[0], {"status": "ok"})
        self.assertEqual(self.request("GET", "/books")[0], [])
        self.request("POST", "/health", expected=405)
        self.request("GET", "/missing", expected=404)

    def test_crud(self):
        fields = dict(title='A "quoted" title', author="Octavia Butler",
                      year=1979, isbn="0123456789")
        book, path = self.create(**fields)
        self.assertEqual(book, dict(fields, id=book["id"]))
        self.assertEqual(self.request("GET", path)[0], book)
        replacement = dict(title="New title", author="New author")
        updated, _ = self.request("PUT", path, replacement)
        self.assertEqual(updated, dict(replacement, id=book["id"], year=None, isbn=None))
        self.assertEqual(self.request("GET", "/books")[0], [updated])
        self.request("DELETE", path, expected=204)
        self.request("GET", path, expected=404)
        self.request("PUT", path, replacement, expected=404)
        self.request("DELETE", path, expected=404)

    def test_author_filter(self):
        author = "José & O'Neil + Co"
        first, _ = self.create(title="First", author=author)
        second, _ = self.create(title="Second", author="Another author")
        third, _ = self.create(title="Third", author=author)
        self.assertEqual(self.request("GET", "/books")[0], [first, second, third])
        query = urlencode({"author": author})
        self.assertEqual(self.request("GET", f"/books?{query}")[0], [first, third])
        self.assertEqual(self.request("GET", "/books?author=missing")[0], [])

    def test_validation(self):
        book, path = self.create(title="Valid", author="Author")
        for body in ({}, {"title": "Only title"}, {"title": " ", "author": "Author"},
                     {"title": "Title", "author": 7},
                     {"title": "Title", "author": "Author", "year": 1.5},
                     {"title": "Title", "author": "Author", "year": 2147483648},
                     {"title": "Title", "author": "Author", "isbn": 123},
                     "[]", '{"title":', '{"title":"a","author":"b"} junk'):
            with self.subTest(body=body):
                self.request("POST", "/books", body, 400)
                self.request("PUT", path, body, 400)
        self.request("GET", "/books/invalid", expected=400)
        self.assertEqual(self.request("GET", "/books")[0], [book])

    def test_persistence(self):
        book, path = self.create(title="Persistent book", author="Author", year=-42)
        self.stop(self.server)
        self.start()
        self.assertEqual(self.request("GET", path)[0], book)


if __name__ == "__main__":
    unittest.main()
