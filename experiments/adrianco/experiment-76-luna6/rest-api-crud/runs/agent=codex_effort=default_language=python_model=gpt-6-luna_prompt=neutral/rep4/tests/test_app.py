import tempfile
import unittest

from app import create_app


class BooksApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(f"{self.temp.name}/books.sqlite").test_client()

    def tearDown(self):
        self.temp.cleanup()

    def create_book(self, **overrides):
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
        payload.update(overrides)
        return self.app.post("/books", json=payload)

    def test_health_and_create_get(self):
        self.assertEqual(self.app.get("/health").json, {"status": "ok"})
        created = self.create_book()
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["title"], "Dune")
        self.assertEqual(self.app.get(f"/books/{created.json['id']}").json["author"], "Frank Herbert")

    def test_validation_and_missing_book(self):
        self.assertEqual(self.app.post("/books", json={"title": "No author"}).status_code, 400)
        self.assertEqual(self.app.post("/books", json={"author": "No title"}).status_code, 400)
        self.assertEqual(self.app.post("/books", json={"title": " ", "author": "Writer"}).status_code, 400)
        self.assertEqual(self.app.get("/books/99").status_code, 404)

    def test_create_accepts_all_fields_and_persists_in_sqlite(self):
        response = self.create_book()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["year"], 1965)
        self.assertEqual(response.json["isbn"], "9780441013593")

        # A separately created app using the same file sees the stored record.
        second_client = create_app(self.temp.name + "/books.sqlite").test_client()
        self.assertEqual(second_client.get("/books").json, [response.json])

    def test_filter_update_delete(self):
        book_id = self.create_book().json["id"]
        self.create_book(title="Foundation", author="Isaac Asimov")
        filtered = self.app.get("/books?author=Frank%20Herbert")
        self.assertEqual(len(filtered.json), 1)
        updated = self.app.put(f"/books/{book_id}", json={"title": "Dune Messiah", "author": "Frank Herbert"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["year"], None)
        self.assertEqual(self.app.delete(f"/books/{book_id}").status_code, 204)
        self.assertEqual(self.app.delete(f"/books/{book_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
