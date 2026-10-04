import io
import json
import tempfile
import unittest

from app import BooksAPI


class BooksAPITest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.app = BooksAPI(self.tempdir.name + "/books.sqlite")

    def tearDown(self):
        self.tempdir.cleanup()

    def request(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path.split("?", 1)[0],
            "QUERY_STRING": path.partition("?")[2],
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        result = {}

        def start_response(status, headers):
            result["status"] = int(status.split()[0])
            result["headers"] = dict(headers)

        result["body"] = b"".join(self.app(environ, start_response))
        result["json"] = json.loads(result["body"]) if result["body"] else None
        return result

    def test_create_get_update_and_delete(self):
        created = self.request("POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"})
        self.assertEqual(created["status"], 201)
        book_id = created["json"]["id"]
        self.assertEqual(self.request("GET", f"/books/{book_id}")["json"]["title"], "Dune")
        updated = self.request("PUT", f"/books/{book_id}", {"title": "Dune Messiah", "author": "Frank Herbert"})
        self.assertEqual(updated["status"], 200)
        self.assertEqual(updated["json"]["title"], "Dune Messiah")
        self.assertIsNone(updated["json"]["year"])
        self.assertEqual(self.request("DELETE", f"/books/{book_id}")["status"], 204)
        self.assertEqual(self.request("GET", f"/books/{book_id}")["status"], 404)

    def test_list_and_filter_by_author(self):
        self.request("POST", "/books", {"title": "One", "author": "A"})
        self.request("POST", "/books", {"title": "Two", "author": "B"})
        self.assertEqual(len(self.request("GET", "/books")["json"]), 2)
        filtered = self.request("GET", "/books?author=B")
        self.assertEqual([book["title"] for book in filtered["json"]], ["Two"])

    def test_validation_health_and_missing_book(self):
        invalid = self.request("POST", "/books", {"title": "Untitled"})
        self.assertEqual(invalid["status"], 400)
        self.assertEqual(self.request("GET", "/health")["json"], {"status": "ok"})
        self.assertEqual(self.request("GET", "/books/999")["status"], 404)


if __name__ == "__main__":
    unittest.main()
