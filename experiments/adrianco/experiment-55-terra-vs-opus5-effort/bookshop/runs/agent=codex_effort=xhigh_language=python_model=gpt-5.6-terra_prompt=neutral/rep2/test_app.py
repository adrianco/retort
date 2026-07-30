"""Integration tests for the book collection API."""

import os
import tempfile
import unittest

from app import create_app


class BooksApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database_file.close()
        self.app = create_app(self.database_file.name)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        os.unlink(self.database_file.name)

    def create_book(self, **overrides):
        payload = {
            "title": "A Wizard of Earthsea",
            "author": "Ursula K. Le Guin",
            "year": 1968,
            "isbn": "978-0-547-77241-5",
        }
        payload.update(overrides)
        return self.client.post("/books", json=payload)

    def test_health_check(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_create_and_get_book(self) -> None:
        created = self.create_book()
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.headers["Location"], "/books/1")
        self.assertEqual(created.get_json()["title"], "A Wizard of Earthsea")

        fetched = self.client.get("/books/1")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["author"], "Ursula K. Le Guin")

    def test_list_can_be_filtered_by_author(self) -> None:
        self.create_book()
        self.create_book(title="The Left Hand of Darkness")
        self.create_book(title="Kindred", author="Octavia E. Butler")

        response = self.client.get("/books?author=Ursula%20K.%20Le%20Guin")
        books = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual([book["title"] for book in books], [
            "A Wizard of Earthsea",
            "The Left Hand of Darkness",
        ])

    def test_update_and_delete_book(self) -> None:
        self.create_book()
        updated = self.client.put("/books/1", json={"year": 1971, "isbn": "new-isbn"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["year"], 1971)
        self.assertEqual(updated.get_json()["title"], "A Wizard of Earthsea")

        deleted = self.client.delete("/books/1")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/books/1").status_code, 404)

    def test_title_and_author_are_required(self) -> None:
        missing_author = self.client.post("/books", json={"title": "Only a title"})
        blank_title = self.client.post("/books", json={"title": " ", "author": "Writer"})
        self.assertEqual(missing_author.status_code, 400)
        self.assertEqual(blank_title.status_code, 400)


if __name__ == "__main__":
    unittest.main()
