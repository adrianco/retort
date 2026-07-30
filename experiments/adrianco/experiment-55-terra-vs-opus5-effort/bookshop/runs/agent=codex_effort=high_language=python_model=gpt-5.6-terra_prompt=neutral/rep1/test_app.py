import os
import tempfile
import unittest

from app import create_app


class BooksApiTest(unittest.TestCase):
    def setUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database_file.close()
        self.app = create_app({"TESTING": True, "DATABASE": self.database_file.name})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.database_file.name)

    def create_book(self, **overrides):
        payload = {"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin",
                   "year": 1969, "isbn": "9780441478125"}
        payload.update(overrides)
        return self.client.post("/books", json=payload)

    def test_create_and_get_book(self):
        created = self.create_book()
        self.assertEqual(created.status_code, 201)
        body = created.get_json()
        self.assertEqual(body["id"], 1)
        self.assertEqual(body["title"], "The Left Hand of Darkness")

        found = self.client.get("/books/1")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.get_json(), body)

    def test_list_can_filter_by_author(self):
        self.create_book(title="A Wizard of Earthsea")
        self.create_book(title="Kindred", author="Octavia E. Butler", year=1979)

        response = self.client.get("/books?author=Ursula%20K.%20Le%20Guin")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([book["title"] for book in response.get_json()], ["A Wizard of Earthsea"])

    def test_update_and_delete_book(self):
        self.create_book()
        updated = self.client.put("/books/1", json={"title": "The Dispossessed", "year": 1974})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["author"], "Ursula K. Le Guin")
        self.assertEqual(updated.get_json()["title"], "The Dispossessed")

        deleted = self.client.delete("/books/1")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/books/1").status_code, 404)

    def test_title_and_author_are_required(self):
        response = self.client.post("/books", json={"title": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.get_json()["message"])

        response = self.client.post("/books", json={"title": "Kindred"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("author", response.get_json()["message"])

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
