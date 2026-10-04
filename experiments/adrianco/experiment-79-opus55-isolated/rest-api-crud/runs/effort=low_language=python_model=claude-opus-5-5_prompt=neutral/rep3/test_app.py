"""Integration tests: run the real server against an in-memory SQLite DB."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from app import make_server, validate_book, ValidationError

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


class BookAPITest(unittest.TestCase):
    def setUp(self):
        self.server = make_server(port=0, db_path=":memory:", quiet=True)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.server.store.close()

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                status, payload = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            with exc:
                status, payload = exc.code, exc.read()
        return status, json.loads(payload) if payload else None

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))

    def test_create_and_get(self):
        status, created = self.request("POST", "/books", DUNE)
        self.assertEqual(status, 201)
        self.assertEqual(created, {"id": created["id"], **DUNE})

        status, fetched = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, created)

    def test_create_with_only_required_fields(self):
        status, created = self.request("POST", "/books", {"title": "T", "author": "A"})
        self.assertEqual(status, 201)
        self.assertIsNone(created["year"])
        self.assertIsNone(created["isbn"])

    def test_create_validation(self):
        status, body = self.request("POST", "/books", {"year": 1965})
        self.assertEqual(status, 422)
        self.assertEqual(set(body["details"]), {"title", "author"})

        status, body = self.request("POST", "/books", {"title": "  ", "author": "A"})
        self.assertEqual(status, 422)
        self.assertIn("title", body["details"])

        status, body = self.request("POST", "/books", {"title": "T", "author": "A", "year": "x"})
        self.assertEqual(status, 422)
        self.assertIn("year", body["details"])

        self.assertEqual(self.request("GET", "/books"), (200, []))

    def test_create_invalid_json(self):
        status, body = self.request("POST", "/books", raw=b"{not json")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

        status, _ = self.request("POST", "/books", raw=b"[1, 2]")
        self.assertEqual(status, 422)

    def test_duplicate_isbn_conflict(self):
        self.request("POST", "/books", DUNE)
        status, _ = self.request("POST", "/books", DUNE)
        self.assertEqual(status, 409)

    def test_list_and_author_filter(self):
        self.request("POST", "/books", DUNE)
        self.request("POST", "/books", {"title": "Emma", "author": "Jane Austen", "year": 1815})
        self.request("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

        status, books = self.request("GET", "/books")
        self.assertEqual(status, 200)
        self.assertEqual([b["title"] for b in books], ["Dune", "Emma", "Persuasion"])

        status, books = self.request("GET", "/books?author=Jane%20Austen")
        self.assertEqual(status, 200)
        self.assertEqual([b["title"] for b in books], ["Emma", "Persuasion"])

        self.assertEqual(self.request("GET", "/books?author=Nobody"), (200, []))

    def test_update(self):
        _, created = self.request("POST", "/books", DUNE)
        path = f"/books/{created['id']}"

        changed = {**DUNE, "title": "Dune Messiah", "year": 1969}
        status, updated = self.request("PUT", path, changed)
        self.assertEqual(status, 200)
        self.assertEqual(updated, {"id": created["id"], **changed})
        self.assertEqual(self.request("GET", path), (200, updated))

        status, _ = self.request("PUT", path, {"title": "No author"})
        self.assertEqual(status, 422)
        self.assertEqual(self.request("GET", path), (200, updated))

    def test_delete(self):
        _, created = self.request("POST", "/books", DUNE)
        path = f"/books/{created['id']}"

        self.assertEqual(self.request("DELETE", path), (204, None))
        self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("DELETE", path)[0], 404)

    def test_not_found(self):
        self.assertEqual(self.request("GET", "/books/999")[0], 404)
        self.assertEqual(self.request("PUT", "/books/999", DUNE)[0], 404)
        self.assertEqual(self.request("GET", "/books/abc")[0], 404)
        self.assertEqual(self.request("GET", "/nope")[0], 404)

    def test_method_not_allowed(self):
        self.assertEqual(self.request("DELETE", "/books")[0], 405)
        self.assertEqual(self.request("POST", "/books/1", DUNE)[0], 405)


class ValidateBookTest(unittest.TestCase):
    def test_strips_whitespace(self):
        book = validate_book({"title": " Dune ", "author": " Frank Herbert "})
        self.assertEqual(book, {"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None})

    def test_rejects_boolean_year(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_book({"title": "T", "author": "A", "year": True})
        self.assertIn("year", ctx.exception.errors)


if __name__ == "__main__":
    unittest.main()
