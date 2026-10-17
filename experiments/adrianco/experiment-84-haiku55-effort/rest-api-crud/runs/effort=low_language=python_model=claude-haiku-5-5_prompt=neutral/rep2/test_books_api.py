"""Integration tests: each test talks to a real server over HTTP."""

import json
import threading
import unittest
import urllib.error
import urllib.request

import tempfile
import os

from books_api import create_server


class BooksApiTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self._tmpdir.name, "test.db")
        self.server = create_server("127.0.0.1", 0, db_path)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server.store.close()
        self._tmpdir.cleanup()

    def request(self, method, path, body=None, raw=None):
        data = raw
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                payload = resp.read()
                return resp.status, dict(resp.headers), _decode(payload)
        except urllib.error.HTTPError as err:
            payload = err.read()
            return err.code, dict(err.headers), _decode(payload)

    def create(self, **overrides):
        book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
        book.update(overrides)
        return self.request("POST", "/books", body=book)


def _decode(payload):
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


class HealthTests(BooksApiTestCase):
    def test_health_returns_ok(self):
        status, _, body = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})


class CreateAndGetTests(BooksApiTestCase):
    def test_create_book_returns_201_with_location(self):
        status, headers, body = self.create()
        self.assertEqual(status, 201)
        self.assertEqual(body["title"], "Dune")
        self.assertEqual(body["author"], "Frank Herbert")
        self.assertEqual(body["year"], 1965)
        self.assertEqual(body["isbn"], "9780441013593")
        self.assertIsInstance(body["id"], int)
        self.assertEqual(headers["Location"], f"/books/{body['id']}")

    def test_get_book_by_id(self):
        _, _, created = self.create()
        status, _, body = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(body, created)

    def test_get_missing_book_returns_404(self):
        status, _, body = self.request("GET", "/books/999")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_optional_year_and_isbn(self):
        status, _, body = self.request("POST", "/books", body={"title": "T", "author": "A"})
        self.assertEqual(status, 201)
        self.assertIsNone(body["year"])
        self.assertIsNone(body["isbn"])


class ListTests(BooksApiTestCase):
    def test_list_empty(self):
        status, _, body = self.request("GET", "/books")
        self.assertEqual(status, 200)
        self.assertEqual(body, [])

    def test_list_all_and_filter_by_author(self):
        self.create(title="Dune", author="Frank Herbert")
        self.create(title="Emma", author="Jane Austen")
        self.create(title="Children of Dune", author="frank herbert")

        _, _, all_books = self.request("GET", "/books")
        self.assertEqual(len(all_books), 3)

        _, _, filtered = self.request("GET", "/books?author=Frank%20Herbert")
        self.assertEqual([b["title"] for b in filtered], ["Dune", "Children of Dune"])

        _, _, none = self.request("GET", "/books?author=Nobody")
        self.assertEqual(none, [])


class UpdateDeleteTests(BooksApiTestCase):
    def test_update_book(self):
        _, _, created = self.create()
        status, _, body = self.request(
            "PUT", f"/books/{created['id']}",
            body={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], created["id"])
        self.assertEqual(body["title"], "Dune Messiah")
        self.assertEqual(body["year"], 1969)
        self.assertIsNone(body["isbn"])

        _, _, fetched = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(fetched, body)

    def test_update_missing_book_returns_404(self):
        status, _, _ = self.request(
            "PUT", "/books/999", body={"title": "T", "author": "A"}
        )
        self.assertEqual(status, 404)

    def test_delete_book(self):
        _, _, created = self.create()
        status, _, body = self.request("DELETE", f"/books/{created['id']}")
        self.assertEqual(status, 204)
        self.assertIsNone(body)

        status, _, _ = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 404)

    def test_delete_missing_book_returns_404(self):
        status, _, _ = self.request("DELETE", "/books/999")
        self.assertEqual(status, 404)


class ValidationTests(BooksApiTestCase):
    def test_missing_title_and_author_rejected(self):
        status, _, body = self.request("POST", "/books", body={"year": 2000})
        self.assertEqual(status, 400)
        self.assertIn("title", body["details"])
        self.assertIn("author", body["details"])

    def test_blank_title_rejected(self):
        status, _, body = self.request("POST", "/books", body={"title": "   ", "author": "A"})
        self.assertEqual(status, 400)
        self.assertIn("title", body["details"])

    def test_bad_year_rejected(self):
        status, _, body = self.request("POST", "/books", body={"title": "T", "author": "A", "year": "1999"})
        self.assertEqual(status, 400)
        self.assertIn("year", body["details"])

    def test_invalid_json_rejected(self):
        status, _, body = self.request("POST", "/books", raw=b"{not json")
        self.assertEqual(status, 400)
        self.assertIn("body", body["details"])

    def test_update_validates_payload(self):
        _, _, created = self.create()
        status, _, _ = self.request("PUT", f"/books/{created['id']}", body={"title": "only"})
        self.assertEqual(status, 400)


class RoutingTests(BooksApiTestCase):
    def test_unknown_path_returns_404(self):
        status, _, _ = self.request("GET", "/nope")
        self.assertEqual(status, 404)

    def test_wrong_method_returns_405_with_allow_header(self):
        status, headers, _ = self.request("PATCH", "/books/1")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET, PUT, DELETE")


if __name__ == "__main__":
    unittest.main()
