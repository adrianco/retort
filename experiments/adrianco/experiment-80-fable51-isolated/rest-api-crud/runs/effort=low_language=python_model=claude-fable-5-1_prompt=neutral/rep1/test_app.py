"""Integration tests: run the API on a real local HTTP server with a temp SQLite DB."""

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

from app import BookApp


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


class BookApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app = BookApp(os.path.join(self.tmp.name, "test.db"))
        self.server = make_server("127.0.0.1", 0, app, handler_class=QuietHandler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None
        )
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                status, content = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            with e:
                status, content = e.code, e.read()
        return status, (json.loads(content) if content else None)

    def create(self, **overrides):
        book = {"title": "Dune", "author": "Frank Herbert", "year": 1965,
                "isbn": "9780441172719"}
        book.update(overrides)
        status, body = self.request("POST", "/books", book)
        self.assertEqual(status, 201)
        return body

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))

    def test_create_and_get(self):
        created = self.create()
        self.assertIsInstance(created["id"], int)
        self.assertEqual(created["title"], "Dune")
        status, fetched = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, created)

    def test_create_optional_fields_omitted(self):
        status, body = self.request("POST", "/books", {"title": "T", "author": "A"})
        self.assertEqual(status, 201)
        self.assertIsNone(body["year"])
        self.assertIsNone(body["isbn"])

    def test_create_validation(self):
        for bad in (
            {"author": "A"},
            {"title": "T"},
            {"title": "  ", "author": "A"},
            {"title": "T", "author": 5},
            {"title": "T", "author": "A", "year": "1965"},
            {"title": "T", "author": "A", "year": True},
            {"title": "T", "author": "A", "isbn": 123},
            ["not", "an", "object"],
        ):
            status, body = self.request("POST", "/books", bad)
            self.assertEqual(status, 400, bad)
            self.assertIn("error", body)
        status, body = self.request("POST", "/books", {})
        self.assertEqual(set(body["details"]), {"title", "author"})
        self.assertEqual(self.request("GET", "/books"), (200, []))

    def test_invalid_json(self):
        status, body = self.request("POST", "/books", raw=b"{nope")
        self.assertEqual(status, 400)
        status, body = self.request("POST", "/books")
        self.assertEqual(status, 400)

    def test_list_and_author_filter(self):
        a = self.create()
        b = self.create(title="Emma", author="Jane Austen", year=1815, isbn=None)
        c = self.create(title="Dune Messiah", year=1969)
        status, books = self.request("GET", "/books")
        self.assertEqual(status, 200)
        self.assertEqual(books, [a, b, c])
        status, books = self.request("GET", "/books?author=Frank%20Herbert")
        self.assertEqual(books, [a, c])
        status, books = self.request("GET", "/books?author=Nobody")
        self.assertEqual((status, books), (200, []))

    def test_update(self):
        created = self.create()
        status, updated = self.request(
            "PUT", f"/books/{created['id']}",
            {"title": "Dune (revised)", "author": "Frank Herbert", "year": 1966},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "Dune (revised)")
        self.assertEqual(updated["year"], 1966)
        self.assertEqual(self.request("GET", f"/books/{created['id']}"), (200, updated))

    def test_update_validation_and_missing(self):
        created = self.create()
        status, _ = self.request("PUT", f"/books/{created['id']}", {"title": "x"})
        self.assertEqual(status, 400)
        status, _ = self.request("PUT", "/books/999", {"title": "x", "author": "y"})
        self.assertEqual(status, 404)

    def test_delete(self):
        created = self.create()
        path = f"/books/{created['id']}"
        self.assertEqual(self.request("DELETE", path), (204, None))
        self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("DELETE", path)[0], 404)

    def test_not_found_and_method_not_allowed(self):
        self.assertEqual(self.request("GET", "/books/999")[0], 404)
        self.assertEqual(self.request("GET", "/books/abc")[0], 404)
        self.assertEqual(self.request("GET", "/nope")[0], 404)
        self.assertEqual(self.request("DELETE", "/books")[0], 405)
        self.assertEqual(self.request("POST", "/health", {})[0], 405)


if __name__ == "__main__":
    unittest.main()
