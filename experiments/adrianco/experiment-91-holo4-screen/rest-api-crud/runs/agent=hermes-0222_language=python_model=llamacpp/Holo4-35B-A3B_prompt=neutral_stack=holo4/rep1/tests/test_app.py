import json
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

CLIENT = os.environ.get("TEST_CLIENT", "wsgi")


class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.db_path = os.path.join(os.path.dirname(__file__), "test_books.db")
        # Use a test database
        import app as a
        a.DATABASE = self.db_path
        a.init_db()
        self.client = app.test_client()

    def tearDown(self):
        os.remove(self.db_path) if os.path.exists(self.db_path) else None

    # ---- Health check ----
    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "ok")

    # ---- Create book ----
    def test_create_book(self):
        resp = self.client.post(
            "/books",
            data=json.dumps({"title": "1984", "author": "George Orwell", "year": 1949}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        book = resp.get_json()
        self.assertEqual(book["title"], "1984")
        self.assertEqual(book["author"], "George Orwell")
        self.assertEqual(book["year"], 1949)
        self.assertIsNotNone(book["id"])

    def test_create_book_missing_title(self):
        resp = self.client.post(
            "/books",
            data=json.dumps({"author": "Someone"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    # ---- List books ----
    def test_list_books(self):
        self.client.post(
            "/books",
            data=json.dumps({"title": "Dune", "author": "Frank Herbert"}),
            content_type="application/json",
        )
        resp = self.client.get("/books")
        self.assertEqual(resp.status_code, 200)
        books = resp.get_json()
        self.assertEqual(len(books), 1)

    def test_list_books_author_filter(self):
        self.client.post(
            "/books",
            data=json.dumps({"title": "Dune", "author": "Frank Herbert"}),
            content_type="application/json",
        )
        self.client.post(
            "/books",
            data=json.dumps({"title": "Neuromancer", "author": "William Gibson"}),
            content_type="application/json",
        )
        resp = self.client.get("/books?author=Frank Herbert")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 1)

    # ---- Get single book ----
    def test_get_book(self):
        post = self.client.post(
            "/books",
            data=json.dumps({"title": "Dune", "author": "Frank Herbert"}),
            content_type="application/json",
        )
        book_id = post.get_json()["id"]
        resp = self.client.get(f"/books/{book_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["title"], "Dune")

    def test_get_book_not_found(self):
        resp = self.client.get("/books/99999")
        self.assertEqual(resp.status_code, 404)

    # ---- Update book ----
    def test_update_book(self):
        post = self.client.post(
            "/books",
            data=json.dumps({"title": "Dune", "author": "Frank Herbert"}),
            content_type="application/json",
        )
        book_id = post.get_json()["id"]
        resp = self.client.put(
            f"/books/{book_id}",
            data=json.dumps({"title": "Dune (Updated)"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["title"], "Dune (Updated)")

    # ---- Delete book ----
    def test_delete_book(self):
        post = self.client.post(
            "/books",
            data=json.dumps({"title": "Dune", "author": "Frank Herbert"}),
            content_type="application/json",
        )
        book_id = post.get_json()["id"]
        resp = self.client.delete(f"/books/{book_id}")
        self.assertEqual(resp.status_code, 204)
        get_resp = self.client.get(f"/books/{book_id}")
        self.assertEqual(get_resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
