import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from app import BookAPI


class BookAPITest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = BookAPI(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def request(self, method, path, payload=None, query=""):
        body = json.dumps(payload).encode() if payload is not None else b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(body),
        }
        result = {}

        def start_response(status, headers):
            result["status"] = int(status.split()[0])
            result["headers"] = dict(headers)

        result["body"] = b"".join(self.app(environ, start_response))
        result["json"] = json.loads(result["body"]) if result["body"] else None
        return result

    def test_create_get_update_and_delete_book(self):
        created = self.request("POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"})
        self.assertEqual(created["status"], 201)
        book_id = created["json"]["id"]
        self.assertEqual(created["headers"]["Location"], f"/books/{book_id}")
        self.assertEqual(self.request("GET", f"/books/{book_id}")["json"]["title"], "Dune")

        updated = self.request("PUT", f"/books/{book_id}", {"title": "Dune Messiah", "author": "Frank Herbert"})
        self.assertEqual(updated["status"], 200)
        self.assertEqual(updated["json"]["title"], "Dune Messiah")
        self.assertIsNone(updated["json"]["year"])

        self.assertEqual(self.request("DELETE", f"/books/{book_id}")["status"], 204)
        self.assertEqual(self.request("GET", f"/books/{book_id}")["status"], 404)

    def test_list_and_author_filter(self):
        self.request("POST", "/books", {"title": "Book A", "author": "Alice"})
        self.request("POST", "/books", {"title": "Book B", "author": "Bob"})
        self.request("POST", "/books", {"title": "Book C", "author": "Alice"})
        self.assertEqual(len(self.request("GET", "/books")["json"]), 3)
        filtered = self.request("GET", "/books", query=urlencode({"author": "Alice"}))
        self.assertEqual([book["title"] for book in filtered["json"]], ["Book A", "Book C"])

    def test_validation_health_and_missing_book(self):
        invalid = self.request("POST", "/books", {"title": "Missing author"})
        self.assertEqual(invalid["status"], 400)
        self.assertEqual(self.request("GET", "/health")["json"], {"status": "ok"})
        self.assertEqual(self.request("GET", "/books/999")["status"], 404)

    def test_invalid_json_is_reported(self):
        result = {}
        body = b"{"
        environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/books", "QUERY_STRING": "", "CONTENT_LENGTH": "1", "wsgi.input": io.BytesIO(body)}
        response = self.app(environ, lambda status, headers: result.update(status=int(status.split()[0])))
        self.assertEqual(result["status"], 400)
        self.assertIn(b"valid JSON", b"".join(response))


if __name__ == "__main__":
    unittest.main()
