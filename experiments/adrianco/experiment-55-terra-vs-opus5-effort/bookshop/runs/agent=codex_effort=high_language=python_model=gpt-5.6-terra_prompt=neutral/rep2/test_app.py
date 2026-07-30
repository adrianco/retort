"""Integration tests for the book API, using the standard-library WSGI test tools."""

import io
import json
import os
import tempfile
import unittest
from wsgiref.util import setup_testing_defaults

from app import create_app


class BookApiTests(unittest.TestCase):
    def setUp(self):
        self.database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database.close()
        self.app = create_app(self.database.name)

    def tearDown(self):
        os.unlink(self.database.name)

    def request(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        environ = {}
        setup_testing_defaults(environ)
        environ.update({
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?", 1)[0],
            "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        })
        if payload is not None:
            environ["CONTENT_TYPE"] = "application/json"
        captured = {}
        response = b"".join(self.app(environ, lambda status, headers: captured.update(status=status, headers=dict(headers))))
        return int(captured["status"].split()[0]), json.loads(response) if response else None, captured["headers"]

    def create_book(self, **overrides):
        book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
        book.update(overrides)
        return self.request("POST", "/books", book)

    def test_create_and_get_a_book(self):
        status, created, headers = self.create_book()
        self.assertEqual(status, 201)
        self.assertEqual(headers["Location"], f"/books/{created['id']}")

        status, fetched, _ = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, created)

    def test_list_can_be_filtered_by_author(self):
        self.create_book()
        self.create_book(title="The Left Hand of Darkness", author="Ursula K. Le Guin")

        status, books, _ = self.request("GET", "/books?author=Frank%20Herbert")
        self.assertEqual(status, 200)
        self.assertEqual([book["title"] for book in books], ["Dune"])

    def test_update_and_delete_a_book(self):
        _, created, _ = self.create_book()
        status, updated, _ = self.request("PUT", f"/books/{created['id']}", {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None})
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "Dune Messiah")

        status, body, _ = self.request("DELETE", f"/books/{created['id']}")
        self.assertEqual((status, body), (204, None))
        self.assertEqual(self.request("GET", f"/books/{created['id']}")[0], 404)

    def test_title_and_author_are_required(self):
        status, body, _ = self.request("POST", "/books", {"title": "", "year": 2020})
        self.assertEqual(status, 400)
        self.assertIn("title", body["error"])

    def test_health_check(self):
        status, body, _ = self.request("GET", "/health")
        self.assertEqual((status, body), (200, {"status": "ok"}))


if __name__ == "__main__":
    unittest.main()
