import io
import json
import tempfile
import unittest

from app import create_app


class BookApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.app = create_app(self.tempdir.name + "/books.sqlite")

    def tearDown(self):
        self.tempdir.cleanup()

    def request(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        path, _, query = path.partition("?")
        status = []

        def start_response(value, headers):
            status.append(int(value.split()[0]))

        result = self.app({
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }, start_response)
        raw = b"".join(result)
        return status[0], json.loads(raw) if raw else None

    def test_create_and_fetch_book(self):
        status, created = self.request("POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"})
        self.assertEqual(status, 201)
        self.assertEqual(created["title"], "Dune")
        self.assertEqual(self.request("GET", f"/books/{created['id']}")[1], created)

    def test_validation_filter_and_missing_book(self):
        self.assertEqual(self.request("POST", "/books", {"title": "", "author": "Someone"})[0], 400)
        self.request("POST", "/books", {"title": "Dune", "author": "Frank Herbert"})
        self.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
        status, results = self.request("GET", "/books?author=Frank%20Herbert")
        self.assertEqual(status, 200)
        self.assertEqual([item["title"] for item in results], ["Dune"])
        self.assertEqual(self.request("GET", "/books/999")[0], 404)

    def test_update_delete_and_health(self):
        _, created = self.request("POST", "/books", {"title": "Old", "author": "Writer"})
        status, updated = self.request("PUT", f"/books/{created['id']}", {"title": "New", "author": "Writer"})
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "New")
        self.assertEqual(self.request("DELETE", f"/books/{created['id']}")[0], 204)
        self.assertEqual(self.request("GET", f"/books/{created['id']}")[0], 404)
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))


if __name__ == "__main__":
    unittest.main()
