import json
import os
import tempfile
import unittest
from email.message import Message
from io import BytesIO

import app


class BookApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        app.DB_PATH = os.path.join(self.tempdir.name, "test.db")

    def tearDown(self):
        self.tempdir.cleanup()

    def request(self, method, path, payload=None):
        class Harness(app.BookHandler):
            def send_response(handler, status, message=None):
                handler.status = status

            def send_header(handler, key, value):
                pass

            def end_headers(handler):
                pass

            def log_message(handler, fmt, *args):
                pass

        handler = Harness.__new__(Harness)
        body = b"" if payload is None else json.dumps(payload).encode()
        handler.path = path
        handler.command = method
        handler.headers = Message()
        handler.headers["Content-Length"] = str(len(body))
        handler.rfile = BytesIO(body)
        handler.wfile = BytesIO()
        getattr(handler, "do_" + method)()
        return handler.status, json.loads(handler.wfile.getvalue())

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))

    def test_create_get_filter_update_delete(self):
        status, book = self.request("POST", "/books", {
            "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"
        })
        self.assertEqual(status, 201)
        book_id = book["id"]
        self.assertEqual(self.request("GET", f"/books/{book_id}")[1]["title"], "Dune")
        self.assertEqual(len(self.request("GET", "/books?author=Frank%20Herbert")[1]), 1)
        status, updated = self.request("PUT", f"/books/{book_id}", {
            "title": "Dune Messiah", "author": "Frank Herbert"
        })
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "Dune Messiah")
        self.assertEqual(self.request("DELETE", f"/books/{book_id}")[0], 200)
        self.assertEqual(self.request("GET", f"/books/{book_id}")[0], 404)

    def test_required_fields_and_missing_book(self):
        self.assertEqual(self.request("POST", "/books", {"title": "No author"})[0], 400)
        self.assertEqual(self.request("GET", "/books/99999")[0], 404)


if __name__ == "__main__":
    unittest.main()
