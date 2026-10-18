"""Tests for the book API."""

import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import BookStore, make_handler, validate_book


class BookApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        database = str(Path(self.tempdir.name) / "test.db")
        self.store = BookStore(database)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def request(self, method: str, path: str, payload=None):
        body = json.dumps(payload) if payload is not None else None
        handler_type = make_handler(self.store)
        handler = object.__new__(handler_type)
        handler.path = path
        handler.headers = {"Content-Length": str(len(body.encode()) if body else 0)}
        handler.rfile = io.BytesIO(body.encode() if body else b"")
        handler.wfile = io.BytesIO()
        handler._headers = {}
        handler._status = None
        handler.send_response = lambda status: setattr(handler, "_status", status)
        handler.send_header = lambda key, value: handler._headers.__setitem__(key, value)
        handler.end_headers = lambda: None
        with patch.object(handler_type, "log_message", lambda *args: None):
            getattr(handler, f"do_{method}")()
        data = handler.wfile.getvalue()
        return handler._status, json.loads(data) if data else None

    def test_health_and_create_then_get_book(self):
        status, result = self.request("GET", "/health")
        self.assertEqual((status, result), (200, {"status": "ok"}))
        status, created = self.request("POST", "/books", {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"})
        self.assertEqual(status, 201)
        self.assertEqual(created["id"], 1)
        status, fetched = self.request("GET", "/books/1")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["title"], "Dune")

    def test_list_filter_update_and_delete(self):
        self.request("POST", "/books", {"title": "Dune", "author": "Frank Herbert"})
        self.request("POST", "/books", {"title": "Foundation", "author": "Isaac Asimov"})
        status, books = self.request("GET", "/books?author=frank%20herbert")
        self.assertEqual(status, 200)
        self.assertEqual([book["title"] for book in books], ["Dune"])
        status, updated = self.request("PUT", "/books/1", {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "Dune Messiah")
        self.assertEqual(self.request("DELETE", "/books/1")[0], 204)
        self.assertEqual(self.request("GET", "/books/1")[0], 404)

    def test_validation_and_missing_resources(self):
        status, error = self.request("POST", "/books", {"title": "", "author": "Nobody"})
        self.assertEqual(status, 400)
        self.assertIn("title", error["error"])
        self.assertEqual(self.request("GET", "/books/999")[0], 404)
        self.assertEqual(self.request("PUT", "/books/999", {"title": "X", "author": "Y"})[0], 404)
        self.assertEqual(self.request("DELETE", "/books/999")[0], 404)


class BookStoreTests(unittest.TestCase):
    def test_validation_requires_title_author_and_valid_optional_fields(self):
        self.assertIsNotNone(validate_book({"title": "T", "author": "A"})[0])
        self.assertIsNotNone(validate_book({"title": " ", "author": "A"})[1])
        self.assertIsNotNone(validate_book({"title": "T", "author": " "})[1])
        self.assertIsNotNone(validate_book({"title": "T", "author": "A", "year": "2000"})[1])


if __name__ == "__main__":
    unittest.main()
