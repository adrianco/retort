"""Integration tests for the book collection API.

Spins up the real HTTP server on an ephemeral port backed by a temporary
SQLite database, then exercises it over HTTP with urllib.
"""

import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app


class BookApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        handler = app.make_app(cls.db_path)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        os.remove(cls.db_path)

    # ---- helpers -------------------------------------------------------
    def request(self, method, path, body=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req) as resp:
                raw = resp.read()
                payload = json.loads(raw) if raw else None
                return resp.status, payload
        except HTTPError as e:
            raw = e.read()
            payload = json.loads(raw) if raw else None
            return e.code, payload

    def create_book(self, **overrides):
        book = {
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt",
            "year": 1999,
            "isbn": "978-0201616224",
        }
        book.update(overrides)
        return self.request("POST", "/books", book)

    # ---- tests ---------------------------------------------------------
    def test_health(self):
        status, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_create_and_get_book(self):
        status, created = self.create_book(title="Clean Code", author="Robert Martin")
        self.assertEqual(status, 201)
        self.assertIn("id", created)
        self.assertEqual(created["title"], "Clean Code")

        status, fetched = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, created)

    def test_create_requires_title_and_author(self):
        status, payload = self.request("POST", "/books", {"author": "Nobody"})
        self.assertEqual(status, 400)
        self.assertIn("title", payload["error"])

        status, payload = self.request("POST", "/books", {"title": "Orphan"})
        self.assertEqual(status, 400)
        self.assertIn("author", payload["error"])

    def test_list_and_author_filter(self):
        self.create_book(title="Book A", author="Filter Author")
        self.create_book(title="Book B", author="Filter Author")
        self.create_book(title="Book C", author="Someone Else")

        status, all_books = self.request("GET", "/books")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(all_books), 3)

        status, filtered = self.request("GET", "/books?author=Filter%20Author")
        self.assertEqual(status, 200)
        self.assertTrue(filtered)
        self.assertTrue(all(b["author"] == "Filter Author" for b in filtered))
        self.assertEqual(len(filtered), 2)

    def test_update_book(self):
        status, created = self.create_book(title="Old Title", author="Author")
        status, updated = self.request(
            "PUT",
            f"/books/{created['id']}",
            {"title": "New Title", "author": "Author", "year": 2020},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "New Title")
        self.assertEqual(updated["year"], 2020)

    def test_delete_book(self):
        status, created = self.create_book()
        status, _ = self.request("DELETE", f"/books/{created['id']}")
        self.assertEqual(status, 204)

        status, _ = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 404)

    def test_get_missing_book_returns_404(self):
        status, payload = self.request("GET", "/books/999999")
        self.assertEqual(status, 404)
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
