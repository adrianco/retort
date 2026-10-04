import io
import json
import sqlite3
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import make_server

import pytest

from app import QuietHandler, create_app

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "9780141439587"}


class Client:
    """Calls the WSGI app in-process and decodes its JSON responses."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, body=None, raw=None):
        path, _, query = path.partition("?")
        if body is not None:
            raw = json.dumps(body).encode("utf-8")
        raw = raw or b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": io.BytesIO(raw),
            "wsgi.errors": io.StringIO(),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        data = b"".join(self.app(environ, start_response))
        payload = json.loads(data) if data else None
        return captured["status"], payload, captured["headers"]

    def get(self, path):
        return self.request("GET", path)[:2]

    def post(self, path, body=None, raw=None):
        return self.request("POST", path, body, raw)[:2]

    def put(self, path, body=None, raw=None):
        return self.request("PUT", path, body, raw)[:2]

    def delete(self, path):
        return self.request("DELETE", path)[:2]


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "books.db")


@pytest.fixture
def client(db_path):
    return Client(create_app(db_path))


def test_health(client):
    assert client.get("/health") == (200, {"status": "ok"})


def test_create_book(client):
    status, book = client.post("/books", DUNE)
    assert status == 201
    assert book == {"id": book["id"], **DUNE}
    assert isinstance(book["id"], int)


def test_create_book_without_optional_fields(client):
    status, book = client.post("/books", {"title": "Dune", "author": "Frank Herbert"})
    assert status == 201
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_trims_whitespace(client):
    status, book = client.post("/books", {"title": "  Dune ", "author": " Frank Herbert "})
    assert status == 201
    assert (book["title"], book["author"]) == ("Dune", "Frank Herbert")


@pytest.mark.parametrize(
    "payload, bad_fields",
    [
        ({"author": "Frank Herbert"}, {"title"}),
        ({"title": "Dune"}, {"author"}),
        ({}, {"title", "author"}),
        ({"title": "", "author": "   "}, {"title", "author"}),
        ({"title": None, "author": 42}, {"title", "author"}),
        ({**DUNE, "year": "1965"}, {"year"}),
        ({**DUNE, "year": 19.65}, {"year"}),
        ({**DUNE, "year": True}, {"year"}),
        ({**DUNE, "year": 10**30}, {"year"}),
        ({**DUNE, "isbn": 9780441013593}, {"isbn"}),
    ],
)
def test_create_rejects_invalid_fields(client, payload, bad_fields):
    status, body = client.post("/books", payload)
    assert status == 400
    assert body["error"] == "Validation failed"
    assert set(body["details"]) == bad_fields
    assert client.get("/books") == (200, [])


@pytest.mark.parametrize("raw", [b"", b"{not json", b"[1, 2]", b'"text"', b"\xff\xfe"])
def test_create_rejects_malformed_body(client, raw):
    status, body = client.post("/books", raw=raw)
    assert status == 400
    assert "error" in body


def test_list_books(client):
    assert client.get("/books") == (200, [])
    _, dune = client.post("/books", DUNE)
    _, emma = client.post("/books", EMMA)
    assert client.get("/books") == (200, [dune, emma])


def test_list_books_filtered_by_author(client):
    _, dune = client.post("/books", DUNE)
    client.post("/books", EMMA)
    _, messiah = client.post("/books", {"title": "Dune Messiah", "author": "Frank Herbert"})

    assert client.get("/books?author=Frank%20Herbert") == (200, [dune, messiah])
    assert client.get("/books?author=frank+herbert") == (200, [dune, messiah])
    assert client.get("/books?author=Frank") == (200, [])
    assert client.get("/books?author=Nobody") == (200, [])


def test_author_filter_is_not_injectable(client):
    client.post("/books", DUNE)
    assert client.get("/books?author=x'%20OR%20'1'='1") == (200, [])


def test_get_book(client):
    _, created = client.post("/books", DUNE)
    assert client.get(f"/books/{created['id']}") == (200, created)


@pytest.mark.parametrize("book_id", ["999", "abc", "-1", "1.5", "9" * 40])
def test_get_missing_book(client, book_id):
    status, body = client.get(f"/books/{book_id}")
    assert status == 404
    assert body == {"error": "Book not found"}


def test_update_book(client):
    _, created = client.post("/books", DUNE)
    changes = {"title": "Dune (Deluxe)", "author": "Frank Herbert", "year": 2019}

    status, updated = client.put(f"/books/{created['id']}", changes)

    assert status == 200
    # PUT replaces the whole resource, so the omitted isbn is cleared.
    assert updated == {"id": created["id"], **changes, "isbn": None}
    assert client.get(f"/books/{created['id']}") == (200, updated)


def test_update_validates_input(client):
    _, created = client.post("/books", DUNE)
    status, body = client.put(f"/books/{created['id']}", {"title": "No author"})
    assert status == 400
    assert set(body["details"]) == {"author"}
    assert client.get(f"/books/{created['id']}") == (200, created)


def test_update_missing_book(client):
    status, body = client.put("/books/999", DUNE)
    assert status == 404
    assert body == {"error": "Book not found"}


def test_delete_book(client):
    _, created = client.post("/books", DUNE)
    assert client.delete(f"/books/{created['id']}") == (204, None)
    assert client.get(f"/books/{created['id']}")[0] == 404
    assert client.delete(f"/books/{created['id']}")[0] == 404
    assert client.get("/books") == (200, [])


def test_unknown_route(client):
    status, body = client.get("/nope")
    assert status == 404
    assert body == {"error": "Not found"}


@pytest.mark.parametrize(
    "method, path, allow",
    [
        ("DELETE", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET"),
    ],
)
def test_method_not_allowed(client, method, path, allow):
    status, body, headers = client.request(method, path)
    assert status == 405
    assert body == {"error": "Method not allowed"}
    assert headers["Allow"] == allow


def test_oversized_body_is_rejected(client):
    status, body = client.post("/books", raw=b" " * (1024 * 1024 + 1))
    assert status == 413
    assert "error" in body


def test_data_is_persisted_in_sqlite(db_path):
    _, created = Client(create_app(db_path)).post("/books", DUNE)

    # A second app instance on the same file sees the data...
    assert Client(create_app(db_path)).get("/books") == (200, [created])

    # ...and so does a plain SQLite connection.
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT title, author, year, isbn FROM books").fetchall()
    conn.close()
    assert rows == [tuple(DUNE.values())]


def test_over_real_http(db_path):
    """End-to-end check through a real socket, as a deployed client would see it."""
    server = make_server("127.0.0.1", 0, create_app(db_path), handler_class=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def call(method, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(base + path, data=data, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read()
                return response.status, response.headers, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, json.loads(exc.read())

    try:
        status, headers, health = call("GET", "/health")
        assert (status, health) == (200, {"status": "ok"})
        assert headers["Content-Type"] == "application/json"

        status, _, book = call("POST", "/books", DUNE)
        assert status == 201

        assert call("GET", "/books?author=Frank%20Herbert")[2] == [book]
        assert call("POST", "/books", {"title": "Dune"})[0] == 400
        assert call("DELETE", f"/books/{book['id']}")[0] == 204
        assert call("GET", f"/books/{book['id']}")[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
