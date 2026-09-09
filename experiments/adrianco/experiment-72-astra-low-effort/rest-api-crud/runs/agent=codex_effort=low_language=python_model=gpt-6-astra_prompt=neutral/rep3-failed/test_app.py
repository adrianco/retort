import tempfile
import unittest
from pathlib import Path

from app import create_app


class BooksAPITest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = {"TESTING": True, "DATABASE": str(Path(self.directory.name) / "test.sqlite3")}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def create(self, **overrides):
        data = {"title": "A Book", "author": "An Author", "year": 2020, "isbn": "9780123456789"}
        data.update(overrides)
        return self.client.post("/books", json=data)

    def test_crud(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        book = response.get_json()
        location = response.headers["Location"]
        self.assertEqual(self.client.get(location).get_json(), book)
        self.assertEqual(self.client.get("/books").get_json(), [book])
        response = self.client.put(location, json={"title": "Revised", "author": "New Author"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": book["id"], "title": "Revised", "author": "New Author", "year": None, "isbn": None})
        self.assertEqual(self.client.delete(location).status_code, 204)
        self.assertEqual(self.client.get(location).status_code, 404)
        self.assertEqual(self.client.get("/books").get_json(), [])

    def test_filter_exact_and_sql_safe(self):
        self.create(author="Alice")
        self.create(author="Bob")
        self.assertEqual(len(self.client.get("/books?author=Alice").get_json()), 1)
        for author in ("alice", "", "' OR 1=1 --"):
            self.assertEqual(self.client.get("/books", query_string={"author": author}).get_json(), [])

    def test_invalid_input(self):
        invalid = [{}, [], None, {"title": "x"}, {"author": "x"}]
        for field, value in [("title", "  "), ("author", 12), ("year", True), ("year", "2020"), ("year", 2**64), ("isbn", 123), ("isbn", " "), ("extra", 1)]:
            invalid.append({"title": "x", "author": "y", field: value})
        for data in invalid:
            with self.subTest(data=data):
                response = self.client.post("/books", data=self.app.json.dumps(data), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
        self.assertEqual(self.client.get("/books").get_json(), [])

    def test_bad_json_and_media_type(self):
        self.assertEqual(self.client.post("/books", data="{", content_type="application/json").status_code, 400)
        response = self.client.post("/books", data="text")
        self.assertEqual(response.status_code, 415)
        self.assertIn("error", response.get_json())

    def test_missing_and_route_errors_are_json(self):
        for path in ("/books/999", "/books/999999999999999999999999", "/books/-1", "/missing"):
            for method in ("get", "put", "delete"):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 404)
                self.assertIn("error", response.get_json())
        self.assertEqual(self.client.patch("/books/1").status_code, 405)

    def test_persistence(self):
        book = self.create().get_json()
        other_client = create_app(self.config).test_client()
        self.assertEqual(other_client.get(f'/books/{book["id"]}').get_json(), book)

    def test_invalid_update_preserves_book(self):
        book = self.create().get_json()
        path = f'/books/{book["id"]}'
        self.assertEqual(self.client.put(path, json={"title": ""}).status_code, 400)
        self.assertEqual(self.client.get(path).get_json(), book)

    def test_health_and_optional_fields(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})
        response = self.client.post("/books", json={"title": " Title ", "author": " Author "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["title"], "Title")
        self.assertIsNone(response.get_json()["year"])
        self.assertIsNone(response.get_json()["isbn"])


if __name__ == "__main__":
    unittest.main()
