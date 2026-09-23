import io
import json
import tempfile
import unittest

from app import create_app


class BookApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(self.temp_dir.name + "/books.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def request(self, method, path, payload=None):
        raw = b"" if payload is None else json.dumps(payload).encode()
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?", 1)[0],
            "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": io.BytesIO(raw),
        }
        result = {}

        def start_response(status, headers):
            result["status"] = int(status.split()[0])
            result["headers"] = dict(headers)

        result["body"] = b"".join(self.app(environ, start_response))
        result["json"] = json.loads(result["body"]) if result["body"] else None
        return result

    def test_create_get_update_delete_book(self):
        created = self.request("POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"})
        self.assertEqual(created["status"], 201)
        book_id = created["json"]["id"]
        self.assertEqual(self.request("GET", f"/books/{book_id}")["json"]["title"], "Dune")
        updated = self.request("PUT", f"/books/{book_id}", {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": None})
        self.assertEqual(updated["json"]["title"], "Dune Messiah")
        self.assertEqual(self.request("DELETE", f"/books/{book_id}")["status"], 204)
        self.assertEqual(self.request("GET", f"/books/{book_id}")["status"], 404)

    def test_list_filters_by_author(self):
        self.request("POST", "/books", {"title": "One", "author": "A"})
        self.request("POST", "/books", {"title": "Two", "author": "B"})
        response = self.request("GET", "/books?author=A")
        self.assertEqual(response["status"], 200)
        self.assertEqual([book["title"] for book in response["json"]], ["One"])

    def test_required_fields_and_health(self):
        invalid = self.request("POST", "/books", {"title": "Missing author"})
        self.assertEqual(invalid["status"], 400)
        self.assertIn("author", invalid["json"]["error"])
        self.assertEqual(self.request("GET", "/health")["json"], {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
