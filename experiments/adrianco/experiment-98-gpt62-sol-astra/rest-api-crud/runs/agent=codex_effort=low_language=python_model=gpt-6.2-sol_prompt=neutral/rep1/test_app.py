from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

from app import create_app


class BookAPITest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "books.sqlite3"
        self.app = validator(create_app(self.database))
        self.book = {
            "title": "Kindred",
            "author": "Octavia E. Butler",
            "year": 1979,
            "isbn": "9780807083697",
        }

    def request(self, method, path, data=None):
        path, _, query = path.partition("?")
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        environ = {}
        setup_testing_defaults(environ)
        environ.update({
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": BytesIO(body),
        })

        def start_response(status_line, response_headers, exc_info=None):
            nonlocal status, headers
            status = int(status_line.split()[0])
            headers = dict(response_headers)

        status, headers = None, None
        response = self.app(environ, start_response)
        try:
            raw = b"".join(response)
        finally:
            response.close()
        if raw:
            self.assertEqual(headers["Content-Type"], "application/json")
        return status, headers, json.loads(raw) if raw else None

    def test_health_and_empty_collection(self):
        status, _, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})
        self.assertEqual(self.request("GET", "/books")[2], [])

    def test_create_fetch_replace_and_delete(self):
        status, headers, created = self.request("POST", "/books", self.book)
        self.assertEqual(status, 201)
        self.assertEqual(created, {"id": created["id"], **self.book})
        path = headers["Location"]
        self.assertEqual(path, f'/books/{created["id"]}')
        self.assertEqual(self.request("GET", path)[2], created)

        replacement = {"title": "Fledgling", "author": self.book["author"]}
        status, _, updated = self.request("PUT", path, replacement)
        self.assertEqual(status, 200)
        self.assertEqual(updated, {
            "id": created["id"], **replacement, "year": None, "isbn": None,
        })
        self.assertEqual(self.request("GET", path)[2], updated)
        self.assertEqual(self.request("DELETE", path), (204, {}, None))
        for method in ("GET", "PUT", "DELETE"):
            with self.subTest(method=method):
                self.assertEqual(self.request(method, path, replacement)[0], 404)

    def test_list_filter_and_persistence(self):
        first = self.request("POST", "/books", self.book)[2]
        second = self.request("POST", "/books", {
            "title": "Beloved", "author": "Toni Morrison",
        })[2]
        self.app = validator(create_app(self.database))
        self.assertEqual(self.request("GET", "/books")[2], [first, second])
        self.assertEqual(
            self.request("GET", "/books?author=Octavia+E.+Butler")[2], [first],
        )
        self.assertEqual(self.request("GET", "/books?author=Unknown")[2], [])

    def test_validation_preserves_collection(self):
        for body in (
            b"{", [], {"title": "Kindred"}, {"author": "Butler"},
            {**self.book, "title": " "}, {**self.book, "author": 1},
            {**self.book, "year": True}, {**self.book, "year": 2**63},
            {**self.book, "isbn": 123},
        ):
            with self.subTest(body=body):
                status, _, error = self.request("POST", "/books", body)
                self.assertEqual(status, 400)
                self.assertIn("error", error)
        self.assertEqual(self.request("GET", "/books")[2], [])

        _, headers, created = self.request("POST", "/books", self.book)
        path = headers["Location"]
        self.assertEqual(self.request("PUT", path, {"title": "Other"})[0], 400)
        self.assertEqual(self.request("GET", path)[2], created)

    def test_unsupported_method_and_unknown_route(self):
        status, headers, error = self.request("PATCH", "/books")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET, POST")
        self.assertIn("error", error)
        self.assertEqual(self.request("GET", "/unknown")[0], 404)


if __name__ == "__main__":
    unittest.main()
