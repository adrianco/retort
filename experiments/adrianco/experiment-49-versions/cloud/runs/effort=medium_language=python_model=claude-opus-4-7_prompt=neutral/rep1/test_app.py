import os
import tempfile
import unittest

from app import create_app


class BooksApiTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app(database=self.db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})

    def test_create_and_get_book(self):
        r = self.client.post(
            "/books",
            json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "978-0"},
        )
        self.assertEqual(r.status_code, 201)
        book = r.get_json()
        self.assertEqual(book["title"], "Dune")
        self.assertEqual(book["author"], "Herbert")
        self.assertEqual(book["year"], 1965)
        book_id = book["id"]

        r = self.client.get(f"/books/{book_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["title"], "Dune")

    def test_create_missing_title(self):
        r = self.client.post("/books", json={"author": "X"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("title", r.get_json()["error"])

    def test_create_missing_author(self):
        r = self.client.post("/books", json={"title": "X"})
        self.assertEqual(r.status_code, 400)

    def test_list_and_filter_by_author(self):
        self.client.post("/books", json={"title": "A", "author": "Alice"})
        self.client.post("/books", json={"title": "B", "author": "Bob"})
        self.client.post("/books", json={"title": "C", "author": "Alice"})

        r = self.client.get("/books")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.get_json()), 3)

        r = self.client.get("/books?author=Alice")
        self.assertEqual(r.status_code, 200)
        results = r.get_json()
        self.assertEqual(len(results), 2)
        self.assertTrue(all(b["author"] == "Alice" for b in results))

    def test_update_book(self):
        r = self.client.post("/books", json={"title": "Old", "author": "A"})
        book_id = r.get_json()["id"]

        r = self.client.put(f"/books/{book_id}", json={"title": "New"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["title"], "New")
        self.assertEqual(r.get_json()["author"], "A")

    def test_update_missing_book(self):
        r = self.client.put("/books/999", json={"title": "X"})
        self.assertEqual(r.status_code, 404)

    def test_delete_book(self):
        r = self.client.post("/books", json={"title": "T", "author": "A"})
        book_id = r.get_json()["id"]

        r = self.client.delete(f"/books/{book_id}")
        self.assertEqual(r.status_code, 204)

        r = self.client.get(f"/books/{book_id}")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
