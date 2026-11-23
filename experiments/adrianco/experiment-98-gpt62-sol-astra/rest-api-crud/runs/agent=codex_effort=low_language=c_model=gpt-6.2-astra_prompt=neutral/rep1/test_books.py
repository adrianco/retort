import http.client
import json
import os
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


class BookService(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "books.db"
        self.live = os.environ.get("BOOKS_TEST_TCP") == "1"
        if not self.live:
            return
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.start()

    def start(self):
        self.server = subprocess.Popen(["./books", str(self.port), str(self.database)])
        self.addCleanup(self.stop, self.server)
        for _ in range(100):
            self.assertIsNone(self.server.poll(), "server exited during startup")
            try:
                if self.request("GET", "/health")[0] == 200:
                    return
            except ConnectionRefusedError:
                time.sleep(0.02)
        self.fail("service did not become ready")

    @staticmethod
    def stop(server):
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=3)

    def request(self, method, path, body=None):
        data = json.dumps(body) if isinstance(body, dict) else body
        if not self.live:
            response = subprocess.check_output(
                ["./test_handler", self.database, method, path, data or ""], text=True)
            status, content_type, payload = response.split("\n", 2)
            self.assertEqual(content_type, "application/json")
            return int(status), json.loads(payload)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            conn.request(method, path, data, {"Content-Type": "application/json"})
            res = conn.getresponse()
            self.assertEqual(res.getheader("Content-Type"), "application/json")
            return res.status, json.loads(res.read())
        finally:
            conn.close()

    def create(self, **fields):
        code, book = self.request("POST", "/books", fields)
        self.assertEqual(code, 201)
        self.assertEqual(book, {"year": None, "isbn": None, **fields, "id": book["id"]})
        return book

    def test_crud_and_persistence(self):
        book = self.create(title="The Dispossessed", author="Ursula K. Le Guin",
                           year=1974, isbn="0060125632")
        path = f"/books/{book['id']}"
        if self.live:
            self.stop(self.server)
            self.start()
        self.assertEqual(self.request("GET", path), (200, book))
        update = {"title": "Lavinia", "author": book["author"], "year": 2008}
        revised = {**update, "id": book["id"], "isbn": None}
        self.assertEqual(self.request("PUT", path, update), (200, revised))
        self.assertEqual(self.request("GET", path), (200, revised))
        self.assertEqual(self.request("DELETE", path), (200, revised))
        for method in ("GET", "DELETE", "PUT"):
            self.assertEqual(self.request(method, path, update)[0], 404)
        self.assertEqual(self.request("GET", "/books"), (200, []))

    def test_filter(self):
        first = self.create(title="One", author="A & B")
        second = self.create(title="Two", author="C")
        self.assertEqual(self.request("GET", "/books"), (200, [first, second]))
        self.assertEqual(self.request("GET", "/books?author=A+%26+B"), (200, [first]))
        self.assertEqual(self.request("GET", "/books?author=missing"), (200, []))

    def test_validation_is_atomic(self):
        book = self.create(title="A", author="B")
        for body in ("{", "[]", "{}", '{"title":"A","author":"B"} garbage',
                     {"title": " ", "author": "A"}, {"title": "X"},
                     {"title": "X", "author": 1},
                     {"title": "X", "author": "Y", "year": "2020"},
                     {"title": "X", "author": "Y", "isbn": 123}):
            with self.subTest(body=body):
                self.assertEqual(self.request("POST", "/books", body)[0], 400)
                self.assertEqual(self.request("PUT", f"/books/{book['id']}", body)[0], 400)
        self.assertEqual(self.request("GET", "/books"), (200, [book]))

    def test_health_and_routing(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))
        self.assertEqual(self.request("PATCH", "/books")[0], 405)
        for path in ("/missing", "/books/12x", "/books/0"):
            self.assertEqual(self.request("GET", path)[0], 404)
