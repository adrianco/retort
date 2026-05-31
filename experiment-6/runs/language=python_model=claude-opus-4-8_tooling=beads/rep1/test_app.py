"""Integration tests for the book collection API.

These use Flask's built-in test client against a temporary SQLite database so
each test run starts from a clean, isolated state. Run with either:

    python -m unittest -v
    python -m pytest -v          # if pytest is installed
"""

import os
import tempfile
import unittest

from app import create_app


class BookApiTestCase(unittest.TestCase):
    def setUp(self):
        # Fresh temp DB file per test for full isolation.
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app(self.db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def _create(self, **payload):
        return self.client.post("/books", json=payload)

    # ----- health ----------------------------------------------------------

    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "ok"})

    # ----- create ----------------------------------------------------------

    def test_create_book(self):
        resp = self._create(
            title="Dune", author="Frank Herbert", year=1965, isbn="978-0441013593"
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(body["title"], "Dune")
        self.assertEqual(body["author"], "Frank Herbert")
        self.assertEqual(body["year"], 1965)
        self.assertIn("id", body)

    def test_create_requires_title_and_author(self):
        resp = self._create(year=2000)
        self.assertEqual(resp.status_code, 400)
        errors = resp.get_json()["errors"]
        self.assertTrue(any("title" in e for e in errors))
        self.assertTrue(any("author" in e for e in errors))

    def test_create_rejects_blank_title(self):
        resp = self._create(title="   ", author="Someone")
        self.assertEqual(resp.status_code, 400)

    def test_create_rejects_non_integer_year(self):
        resp = self._create(title="X", author="Y", year="nineteen")
        self.assertEqual(resp.status_code, 400)

    # ----- list / filter ---------------------------------------------------

    def test_list_and_author_filter(self):
        self._create(title="A Game of Thrones", author="George R. R. Martin")
        self._create(title="Dune", author="Frank Herbert")
        self._create(title="Dune Messiah", author="Frank Herbert")

        all_books = self.client.get("/books").get_json()
        self.assertEqual(len(all_books), 3)

        filtered = self.client.get("/books?author=Frank Herbert").get_json()
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(b["author"] == "Frank Herbert" for b in filtered))

    # ----- get single ------------------------------------------------------

    def test_get_single(self):
        created = self._create(title="1984", author="George Orwell").get_json()
        resp = self.client.get(f"/books/{created['id']}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["title"], "1984")

    def test_get_missing_returns_404(self):
        resp = self.client.get("/books/9999")
        self.assertEqual(resp.status_code, 404)

    # ----- update ----------------------------------------------------------

    def test_update_book(self):
        created = self._create(title="Old Title", author="Author").get_json()
        resp = self.client.put(
            f"/books/{created['id']}", json={"title": "New Title", "year": 2021}
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["title"], "New Title")
        self.assertEqual(body["year"], 2021)
        self.assertEqual(body["author"], "Author")  # unchanged

    def test_update_missing_returns_404(self):
        resp = self.client.put("/books/9999", json={"title": "x"})
        self.assertEqual(resp.status_code, 404)

    def test_update_rejects_blank_author(self):
        created = self._create(title="T", author="A").get_json()
        resp = self.client.put(f"/books/{created['id']}", json={"author": ""})
        self.assertEqual(resp.status_code, 400)

    # ----- delete ----------------------------------------------------------

    def test_delete_book(self):
        created = self._create(title="To Delete", author="A").get_json()
        resp = self.client.delete(f"/books/{created['id']}")
        self.assertEqual(resp.status_code, 204)
        # Confirm it is gone.
        self.assertEqual(self.client.get(f"/books/{created['id']}").status_code, 404)

    def test_delete_missing_returns_404(self):
        resp = self.client.delete("/books/9999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
