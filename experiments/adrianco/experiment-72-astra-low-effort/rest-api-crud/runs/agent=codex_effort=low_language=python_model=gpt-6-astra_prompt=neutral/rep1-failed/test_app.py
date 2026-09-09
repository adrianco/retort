import json
import os
import tempfile
import unittest

from app import create_app


class BooksAPITest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = {"TESTING": True, "DATABASE": os.path.join(self.directory.name, "test.db")}
        self.client = create_app(self.config).test_client()
        self.book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "0441172717"}

    def tearDown(self):
        self.directory.cleanup()

    def test_crud(self):
        response = self.client.post("/books", json=self.book)
        self.assertEqual(response.status_code, 201)
        path = response.headers["Location"]
        expected = dict(self.book, id=response.json["id"])
        self.assertEqual(self.client.get(path).json, expected)
        self.assertEqual(self.client.get("/books").json, [expected])
        response = self.client.put(path, json={"title": "Updated", "author": "Someone"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, dict(id=expected["id"], title="Updated", author="Someone", year=None, isbn=None))
        self.assertEqual(self.client.get(path).json, response.json)
        self.assertEqual(self.client.delete(path).status_code, 200)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get("/books").json, [])

    def test_author_filter(self):
        self.client.post("/books", json=self.book)
        self.client.post("/books", json={"title": "Other", "author": "Other"})
        response = self.client.get("/books", query_string={"author": "Frank Herbert"})
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]["title"], "Dune")
        self.assertEqual(self.client.get("/books", query_string={"author": "' OR 1=1 --"}).json, [])

    def test_validation(self):
        invalid = [{}, [], None, {"title": "Only title"}, dict(self.book, title="  "),
                   dict(self.book, author=42), dict(self.book, year=True),
                   dict(self.book, year="1965"), dict(self.book, isbn=123)]
        for data in invalid:
            with self.subTest(data=data):
                response = self.client.post("/books", data=json.dumps(data), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)
        self.assertEqual(self.client.get("/books").json, [])

    def test_invalid_update_preserves_book(self):
        original = self.client.post("/books", json=self.book)
        path = original.headers["Location"]
        self.assertEqual(self.client.put(path, json={"author": "Changed"}).status_code, 400)
        self.assertEqual(self.client.get(path).json, original.json)

    def test_missing_and_protocol_errors_are_json(self):
        for method in ("get", "delete", "put"):
            response = getattr(self.client, method)("/books/999", json=self.book)
            self.assertEqual(response.status_code, 404)
            self.assertIn("error", response.json)
        for path in ("/unknown", "/books/not-an-id"):
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertTrue(self.client.get(path).is_json)
        self.assertEqual(self.client.patch("/books/1").status_code, 405)
        malformed = self.client.post("/books", data="{", content_type="application/json")
        self.assertEqual(malformed.status_code, 400)
        self.assertTrue(malformed.is_json)
        self.assertEqual(self.client.post("/books", data="text").status_code, 415)

    def test_health_and_persistence(self):
        self.assertEqual(self.client.get("/health").json, {"status": "ok"})
        self.assertEqual(self.client.get("/health").status_code, 200)
        original = self.client.post("/books", json=self.book).json
        reopened = create_app(self.config).test_client()
        self.assertEqual(reopened.get("/books").json, [original])


if __name__ == "__main__":
    unittest.main()
