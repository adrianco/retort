"""Integration tests for the Book API."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import app


def _request(method: str, url: str, body: dict | None = None) -> tuple[int, dict | list | None]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            payload = json.loads(raw.decode("utf-8")) if raw else None
            return resp.status, payload
    except urllib.error.HTTPError as e:
        try:
            raw = e.read()
        finally:
            e.close()
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError:
            payload = None
        return e.code, payload


class BookAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls._tmpdir.name, "test.db")
        app.init_db(cls.db_path)
        handler = app.make_handler(cls.db_path)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls._tmpdir.cleanup()

    def setUp(self) -> None:
        with app.get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM books")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='books'")

    def _create(self, **kwargs) -> dict:
        payload = {"title": "T", "author": "A", "year": 2020, "isbn": "x"}
        payload.update(kwargs)
        status, body = _request("POST", f"{self.base}/books", payload)
        self.assertEqual(status, 201, body)
        assert isinstance(body, dict)
        return body

    # --- health
    def test_health_endpoint(self):
        status, body = _request("GET", f"{self.base}/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    # --- create
    def test_create_book_returns_201_with_body(self):
        status, body = _request(
            "POST",
            f"{self.base}/books",
            {"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "978-0441172719"},
        )
        self.assertEqual(status, 201)
        assert isinstance(body, dict)
        self.assertEqual(body["title"], "Dune")
        self.assertEqual(body["author"], "Herbert")
        self.assertEqual(body["year"], 1965)
        self.assertEqual(body["isbn"], "978-0441172719")
        self.assertIn("id", body)

    def test_create_missing_title_returns_400(self):
        status, body = _request("POST", f"{self.base}/books", {"author": "Herbert"})
        self.assertEqual(status, 400)
        assert isinstance(body, dict)
        self.assertIn("title", body["error"])

    def test_create_missing_author_returns_400(self):
        status, body = _request("POST", f"{self.base}/books", {"title": "Dune"})
        self.assertEqual(status, 400)
        assert isinstance(body, dict)
        self.assertIn("author", body["error"])

    def test_create_empty_title_returns_400(self):
        status, _ = _request("POST", f"{self.base}/books", {"title": "   ", "author": "A"})
        self.assertEqual(status, 400)

    def test_create_invalid_json_returns_400(self):
        req = urllib.request.Request(
            f"{self.base}/books",
            data=b"not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                self.fail(f"expected 400, got {resp.status}")
        except urllib.error.HTTPError as e:
            e.close()
            self.assertEqual(e.code, 400)

    # --- list
    def test_list_books_empty(self):
        status, body = _request("GET", f"{self.base}/books")
        self.assertEqual(status, 200)
        self.assertEqual(body, [])

    def test_list_books_returns_all(self):
        self._create(title="Book A", author="Alice")
        self._create(title="Book B", author="Bob")
        status, body = _request("GET", f"{self.base}/books")
        self.assertEqual(status, 200)
        assert isinstance(body, list)
        self.assertEqual(len(body), 2)

    def test_list_books_filters_by_author(self):
        self._create(title="Book A", author="Alice")
        self._create(title="Book B", author="Bob")
        self._create(title="Book C", author="Alice")
        status, body = _request("GET", f"{self.base}/books?author=Alice")
        self.assertEqual(status, 200)
        assert isinstance(body, list)
        self.assertEqual(len(body), 2)
        self.assertTrue(all(b["author"] == "Alice" for b in body))

    # --- get one
    def test_get_book_by_id(self):
        created = self._create(title="Dune", author="Herbert")
        status, body = _request("GET", f"{self.base}/books/{created['id']}")
        self.assertEqual(status, 200)
        assert isinstance(body, dict)
        self.assertEqual(body["title"], "Dune")

    def test_get_book_missing_returns_404(self):
        status, body = _request("GET", f"{self.base}/books/9999")
        self.assertEqual(status, 404)
        assert isinstance(body, dict)
        self.assertIn("error", body)

    def test_get_book_invalid_id_returns_400(self):
        status, _ = _request("GET", f"{self.base}/books/abc")
        self.assertEqual(status, 400)

    # --- update
    def test_update_book_full(self):
        created = self._create(title="Old", author="A")
        status, body = _request(
            "PUT",
            f"{self.base}/books/{created['id']}",
            {"title": "New", "author": "B", "year": 2024, "isbn": "z"},
        )
        self.assertEqual(status, 200)
        assert isinstance(body, dict)
        self.assertEqual(body["title"], "New")
        self.assertEqual(body["author"], "B")
        self.assertEqual(body["year"], 2024)

    def test_update_book_partial(self):
        created = self._create(title="Old", author="A", year=1999)
        status, body = _request(
            "PUT", f"{self.base}/books/{created['id']}", {"title": "Renamed"}
        )
        self.assertEqual(status, 200)
        assert isinstance(body, dict)
        self.assertEqual(body["title"], "Renamed")
        self.assertEqual(body["author"], "A")
        self.assertEqual(body["year"], 1999)

    def test_update_missing_book_returns_404(self):
        status, _ = _request("PUT", f"{self.base}/books/9999", {"title": "X"})
        self.assertEqual(status, 404)

    def test_update_invalid_field_returns_400(self):
        created = self._create()
        status, _ = _request(
            "PUT", f"{self.base}/books/{created['id']}", {"title": ""}
        )
        self.assertEqual(status, 400)

    # --- delete
    def test_delete_book(self):
        created = self._create()
        status, _ = _request("DELETE", f"{self.base}/books/{created['id']}")
        self.assertEqual(status, 204)
        status, _ = _request("GET", f"{self.base}/books/{created['id']}")
        self.assertEqual(status, 404)

    def test_delete_missing_book_returns_404(self):
        status, _ = _request("DELETE", f"{self.base}/books/9999")
        self.assertEqual(status, 404)

    # --- routing
    def test_unknown_route_returns_404(self):
        status, _ = _request("GET", f"{self.base}/unknown")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
