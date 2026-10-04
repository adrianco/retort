import tempfile
import unittest
from pathlib import Path

from app import create_app


class BooksAPITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = {"TESTING": True, "DATABASE": str(Path(self.temp.name) / "books.db")}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}

    def test_crud(self):
        response = self.client.post("/books", json=self.book)
        self.assertEqual(response.status_code, 201)
        location = response.headers["Location"]
        expected = dict(self.book, id=response.json["id"])
        self.assertEqual(response.json, expected)
        self.assertEqual(self.client.get(location).json, expected)
        self.assertEqual(self.client.get("/books").json, [expected])
        replacement = {"title": "Dune Messiah", "author": "Frank Herbert"}
        updated = self.client.put(location, json=replacement)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json, dict(replacement, id=expected["id"], year=None, isbn=None))
        self.assertEqual(self.client.get(location).json, updated.json)
        deleted = self.client.delete(location)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(deleted.data, b"")
        self.assertEqual(self.client.get(location).status_code, 404)
        self.assertEqual(self.client.get("/books").json, [])

    def test_author_filter(self):
        self.client.post("/books", json=self.book)
        other = {"title": "Other", "author": "O'Brian"}
        self.client.post("/books", json=other)
        result = self.client.get("/books", query_string={"author": "O'Brian"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual([book["title"] for book in result.json], ["Other"])
        self.assertEqual(self.client.get("/books?author=Nobody").json, [])
        self.assertEqual(self.client.get("/books", query_string={"author": "' OR 1=1 --"}).json, [])

    def test_invalid_fields(self):
        invalid = [{}, [], {"title": "Only"}]
        for field, values in {"title": [None, "", "  ", 1], "author": [None, "", [], True],
                              "year": [True, "1965", 0, 10000, 1.5], "isbn": [123, "", []]}.items():
            invalid.extend(dict(self.book, **{field: value}) for value in values)
        invalid.append(dict(self.book, unexpected="value"))
        for payload in invalid:
            with self.subTest(payload=payload):
                response = self.client.post("/books", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)
        self.assertEqual(self.client.get("/books").json, [])

    def test_invalid_update_preserves_book(self):
        created = self.client.post("/books", json=self.book)
        location = created.headers["Location"]
        self.assertEqual(self.client.put(location, json={"title": "Missing author"}).status_code, 400)
        self.assertEqual(self.client.get(location).json, created.json)

    def test_invalid_bodies(self):
        for body, content_type in [("{", "application/json"), ("null", "application/json"),
                                   ("text", "text/plain")]:
            response = self.client.post("/books", data=body, content_type=content_type)
            self.assertEqual(response.status_code, 400)
            self.assertIn("error", response.json)

    def test_missing_books_and_routes(self):
        for response in [self.client.get("/books/99"), self.client.put("/books/99", json=self.book),
                         self.client.delete("/books/99"), self.client.get("/missing"),
                         self.client.get("/books/abc")]:
            self.assertEqual(response.status_code, 404)
            self.assertIn("error", response.json)
        response = self.client.patch("/books/1", json=self.book)
        self.assertEqual(response.status_code, 405)
        self.assertIn("error", response.json)
        self.assertIn("Allow", response.headers)

    def test_health_and_empty_list(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertEqual(self.client.get("/books").json, [])

    def test_persistence(self):
        created = self.client.post("/books", json=self.book).json
        second_client = create_app(self.config).test_client()
        self.assertEqual(second_client.get(f"/books/{created['id']}").json, created)

    def test_update_and_delete_persistence(self):
        created = self.client.post("/books", json=self.book)
        location = created.headers["Location"]
        replacement = dict(self.book, title="Dune Messiah", year=1969, isbn="9780441172696")
        updated = self.client.put(location, json=replacement)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json, dict(replacement, id=created.json["id"]))
        restarted = create_app(self.config).test_client()
        self.assertEqual(restarted.get(location).json, updated.json)
        self.assertEqual(restarted.delete(location).status_code, 204)
        restarted = create_app(self.config).test_client()
        self.assertEqual(restarted.get(location).status_code, 404)
        self.assertEqual(restarted.get("/books").json, [])

    def test_required_fields_on_create_and_update(self):
        created = self.client.post("/books", json=self.book)
        location = created.headers["Location"]
        for field in ("title", "author"):
            payload = dict(self.book)
            del payload[field]
            for method, path in ((self.client.post, "/books"), (self.client.put, location)):
                with self.subTest(field=field, method=method.__name__):
                    response = method(path, json=payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertTrue(response.is_json)
        self.assertEqual(self.client.get("/books").json, [created.json])


if __name__ == "__main__":
    unittest.main()
