import json
import os
import sqlite3
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))


def request(method, url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


class BookApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        try:
            cls.port = cls._free_port()
        except PermissionError as error:
            cls.tmp.cleanup()
            raise unittest.SkipTest(f"network binding is unavailable: {error}")
        env = os.environ.copy()
        env["PORT"] = str(cls.port)
        env["BOOKS_DB"] = os.path.join(cls.tmp.name, "test.db")
        cls.server = subprocess.Popen([os.path.join(ROOT, "book_service")], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(50):
            if cls.server.poll() is not None:
                raise RuntimeError("server exited during startup")
            try:
                if request("GET", cls.base + "/health")[0] == 200:
                    break
            except Exception:
                time.sleep(0.05)
        else:
            raise RuntimeError("server did not start")

    @staticmethod
    def _free_port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait()
        cls.tmp.cleanup()

    def test_health_and_create_validation(self):
        self.assertEqual(request("GET", self.base + "/health"), (200, {"status": "ok"}))
        status, body = request("POST", self.base + "/books", {"title": "Only title"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_create_list_filter_and_get(self):
        status, book = request("POST", self.base + "/books", {
            "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"
        })
        self.assertEqual(status, 201)
        self.assertEqual(book["title"], "Dune")
        self.assertEqual(request("GET", self.base + "/books")[0], 200)
        status, filtered = request("GET", self.base + "/books?author=Frank%20Herbert")
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in filtered], [book["id"]])
        status, fetched = request("GET", self.base + f"/books/{book['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["isbn"], "123")

    def test_update_and_delete(self):
        _, book = request("POST", self.base + "/books", {"title": "Old", "author": "A"})
        status, changed = request("PUT", self.base + f"/books/{book['id']}", {
            "title": "New", "author": "B", "year": 2024, "isbn": "XYZ"
        })
        self.assertEqual(status, 200)
        self.assertEqual((changed["title"], changed["author"], changed["year"]), ("New", "B", 2024))
        self.assertEqual(request("DELETE", self.base + f"/books/{book['id']}")[0], 200)
        self.assertEqual(request("GET", self.base + f"/books/{book['id']}")[0], 404)


class StorageTest(unittest.TestCase):
    def test_sqlite_book_crud_and_author_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(os.path.join(tmp, "books.db"))
            db.execute("CREATE TABLE books(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,author TEXT NOT NULL,year INTEGER NOT NULL DEFAULT 0,isbn TEXT NOT NULL DEFAULT '')")
            db.execute("INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", ("Dune", "Frank Herbert", 1965, "123"))
            db.execute("INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", ("Foundation", "Isaac Asimov", 1951, "456"))
            self.assertEqual(db.execute("SELECT title FROM books WHERE author=?", ("Frank Herbert",)).fetchone(), ("Dune",))
            db.execute("UPDATE books SET title=?,year=? WHERE id=1", ("Dune Messiah", 1969))
            self.assertEqual(db.execute("SELECT title,year FROM books WHERE id=1").fetchone(), ("Dune Messiah", 1969))
            db.execute("DELETE FROM books WHERE id=2")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM books").fetchone(), (1,))
            db.close()


if __name__ == "__main__":
    unittest.main()
