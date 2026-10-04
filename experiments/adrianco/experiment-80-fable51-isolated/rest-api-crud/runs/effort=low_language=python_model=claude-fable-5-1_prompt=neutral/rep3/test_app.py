import io
import json
import unittest

from app import BookApp


class BookApiTest(unittest.TestCase):
    def setUp(self):
        self.app = BookApp(":memory:")
        self.addCleanup(self.app.close)

    def request(self, method, path, body=None, raw=None):
        path, _, query = path.partition("?")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(data)),
            "wsgi.input": io.BytesIO(data),
        }
        result = {}

        def start_response(status, headers):
            result["status"] = int(status.split()[0])

        out = b"".join(self.app(environ, start_response))
        return result["status"], (json.loads(out) if out else None)

    def create(self, **overrides):
        book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
        book.update(overrides)
        return self.request("POST", "/books", book)

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))

    def test_create_and_get(self):
        status, book = self.create()
        self.assertEqual(status, 201)
        self.assertEqual(book["title"], "Dune")
        self.assertIn("id", book)
        status, fetched = self.request("GET", f"/books/{book['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, book)

    def test_create_optional_fields_omitted(self):
        status, book = self.request("POST", "/books", {"title": "T", "author": "A"})
        self.assertEqual(status, 201)
        self.assertIsNone(book["year"])
        self.assertIsNone(book["isbn"])

    def test_create_validation(self):
        status, body = self.request("POST", "/books", {"author": "A"})
        self.assertEqual(status, 400)
        self.assertIn("title", body["details"])
        status, body = self.request("POST", "/books", {"title": "T", "author": "  "})
        self.assertEqual(status, 400)
        self.assertIn("author", body["details"])
        status, body = self.create(year="1965")
        self.assertEqual(status, 400)
        self.assertIn("year", body["details"])
        self.assertEqual(self.request("GET", "/books"), (200, []))

    def test_invalid_json(self):
        status, _ = self.request("POST", "/books", raw=b"{nope")
        self.assertEqual(status, 400)
        status, _ = self.request("POST", "/books", raw=b"[1]")
        self.assertEqual(status, 400)

    def test_list_and_author_filter(self):
        self.create()
        self.create(title="Emma", author="Jane Austen")
        status, books = self.request("GET", "/books")
        self.assertEqual(status, 200)
        self.assertEqual(len(books), 2)
        status, books = self.request("GET", "/books?author=Jane%20Austen")
        self.assertEqual(status, 200)
        self.assertEqual([b["title"] for b in books], ["Emma"])
        self.assertEqual(self.request("GET", "/books?author=Nobody"), (200, []))

    def test_update(self):
        _, book = self.create()
        status, updated = self.request(
            "PUT", f"/books/{book['id']}", {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "Dune Messiah")
        self.assertEqual(updated["year"], 1969)
        status, _ = self.request("PUT", f"/books/{book['id']}", {"title": ""})
        self.assertEqual(status, 400)
        status, _ = self.request("PUT", "/books/999", {"title": "T", "author": "A"})
        self.assertEqual(status, 404)

    def test_delete(self):
        _, book = self.create()
        self.assertEqual(self.request("DELETE", f"/books/{book['id']}"), (204, None))
        self.assertEqual(self.request("GET", f"/books/{book['id']}")[0], 404)
        self.assertEqual(self.request("DELETE", f"/books/{book['id']}")[0], 404)

    def test_unknown_route_and_method(self):
        self.assertEqual(self.request("GET", "/nope")[0], 404)
        self.assertEqual(self.request("PATCH", "/books")[0], 405)


if __name__ == "__main__":
    unittest.main()
