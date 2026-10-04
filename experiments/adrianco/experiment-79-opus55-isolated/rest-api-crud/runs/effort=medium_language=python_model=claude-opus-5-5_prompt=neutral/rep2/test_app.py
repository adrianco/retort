"""Integration tests: each test drives a real server over HTTP with its own SQLite file."""

import json
import socket
import threading
import urllib.error
import urllib.request

import pytest

from app import BookStore, create_server

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "9780141439587"}


class Client:
    def __init__(self, base_url):
        self.base_url = base_url

    def request(self, method, path, body=None, raw=None):
        """Return (status, decoded JSON body or None, headers)."""
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status, headers, payload = resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as err:
            status, headers, payload = err.code, err.headers, err.read()
        return status, (json.loads(payload) if payload else None), headers

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body):
        return self.request("POST", path, body)

    def put(self, path, body):
        return self.request("PUT", path, body)

    def delete(self, path):
        return self.request("DELETE", path)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "books.db")


@pytest.fixture
def client(db_path):
    server = create_server(port=0, db_path=db_path, quiet=True)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield Client(f"http://127.0.0.1:{server.server_address[1]}")
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_health(client):
    status, body, headers = client.get("/health")
    assert status == 200
    assert body == {"status": "ok"}
    assert headers["Content-Type"].startswith("application/json")


def test_create_book(client):
    status, body, headers = client.post("/books", DUNE)
    assert status == 201
    assert body == {"id": body["id"], **DUNE}
    assert isinstance(body["id"], int)
    assert headers["Location"] == f"/books/{body['id']}"


def test_create_book_with_only_required_fields(client):
    status, body, _ = client.post("/books", {"title": "  Dune ", "author": "Frank Herbert"})
    assert status == 201
    assert body == {"id": body["id"], "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


@pytest.mark.parametrize(
    "payload, bad_fields",
    [
        ({"author": "Frank Herbert"}, {"title"}),
        ({"title": "Dune"}, {"author"}),
        ({}, {"title", "author"}),
        ({"title": "", "author": "   "}, {"title", "author"}),
        ({"title": None, "author": 42}, {"title", "author"}),
        ({**DUNE, "year": "1965"}, {"year"}),
        ({**DUNE, "year": True}, {"year"}),
        ({**DUNE, "year": 1965.5}, {"year"}),
        ({**DUNE, "isbn": 9780441172719}, {"isbn"}),
    ],
)
def test_create_book_validation(client, payload, bad_fields):
    status, body, _ = client.post("/books", payload)
    assert status == 400
    assert body["error"] == "Validation failed"
    assert set(body["details"]) == bad_fields
    assert client.get("/books")[1] == []


@pytest.mark.parametrize("raw", [b"{not json", b"", b"[1, 2]", b'"text"', b"\xff\xfe"])
def test_create_book_rejects_malformed_body(client, raw):
    status, body, _ = client.request("POST", "/books", raw=raw)
    assert status == 400
    assert "error" in body


def test_get_book(client):
    created = client.post("/books", DUNE)[1]
    status, body, _ = client.get(f"/books/{created['id']}")
    assert status == 200
    assert body == created


@pytest.mark.parametrize("book_id", ["999", "abc", "-1", "1.5", "9" * 40])
def test_get_missing_book(client, book_id):
    status, body, _ = client.get(f"/books/{book_id}")
    assert status == 404
    assert body == {"error": "Book not found"}


def test_list_books(client):
    assert client.get("/books")[:2] == (200, [])
    dune = client.post("/books", DUNE)[1]
    emma = client.post("/books", EMMA)[1]
    status, body, _ = client.get("/books")
    assert status == 200
    assert body == [dune, emma]


def test_list_books_filtered_by_author(client):
    dune = client.post("/books", DUNE)[1]
    client.post("/books", EMMA)
    messiah = client.post("/books", {"title": "Dune Messiah", "author": "Frank Herbert"})[1]

    assert client.get("/books?author=Frank%20Herbert")[1] == [dune, messiah]
    assert client.get("/books?author=frank+herbert")[1] == [dune, messiah]
    assert client.get("/books?author=Frank")[1] == []
    assert client.get("/books?author=Nobody")[:2] == (200, [])


def test_author_filter_is_not_sql_injectable(client):
    client.post("/books", DUNE)
    assert client.get("/books?author=x%27%20OR%20%271%27%3D%271")[:2] == (200, [])


def test_update_book(client):
    created = client.post("/books", DUNE)[1]
    changes = {"title": "Dune (Revised)", "author": "F. Herbert", "year": 1966}
    status, body, _ = client.put(f"/books/{created['id']}", changes)
    assert status == 200
    # PUT replaces the whole resource, so the omitted isbn is cleared.
    assert body == {"id": created["id"], **changes, "isbn": None}
    assert client.get(f"/books/{created['id']}")[1] == body


def test_update_book_validation(client):
    created = client.post("/books", DUNE)[1]
    status, body, _ = client.put(f"/books/{created['id']}", {"title": "No Author"})
    assert status == 400
    assert set(body["details"]) == {"author"}
    assert client.get(f"/books/{created['id']}")[1] == created


def test_update_missing_book(client):
    status, body, _ = client.put("/books/999", DUNE)
    assert status == 404
    assert body == {"error": "Book not found"}


def test_delete_book(client):
    created = client.post("/books", DUNE)[1]
    status, body, _ = client.delete(f"/books/{created['id']}")
    assert status == 204
    assert body is None
    assert client.get(f"/books/{created['id']}")[0] == 404
    assert client.delete(f"/books/{created['id']}")[0] == 404


def test_unknown_route(client):
    status, body, _ = client.get("/nope")
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
    status, body, headers = client.request(method, path, body=DUNE)
    assert status == 405
    assert body == {"error": "Method not allowed"}
    assert headers["Allow"] == allow


def test_oversized_body_rejected(client):
    # The server refuses on the declared length without reading the body, so
    # declare a large body over a raw socket rather than actually uploading one.
    host, port = client.base_url.removeprefix("http://").split(":")
    with socket.create_connection((host, int(port)), timeout=5) as sock:
        sock.sendall(b"POST /books HTTP/1.1\r\nHost: x\r\nContent-Length: 1048577\r\n\r\n")
        response = sock.makefile("rb").read()
    head, _, payload = response.partition(b"\r\n\r\n")
    assert head.split(b"\r\n")[0].split()[1] == b"413"
    assert json.loads(payload) == {"error": "Request body too large"}
    assert client.get("/books")[1] == []


def test_data_persists_across_store_instances(db_path):
    created = BookStore(db_path).create({**DUNE})
    assert BookStore(db_path).get(created["id"]) == created
