import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


class Client:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, body=None, raw=None):
        path, _, query = path.partition("?")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(data)),
            "wsgi.input": io.BytesIO(data),
        }
        out = b"".join(self.app(environ, start_response))
        parsed = json.loads(out) if out else None
        return captured["status"], parsed, captured["headers"]


@pytest.fixture
def client(tmp_path):
    return Client(create_app(str(tmp_path / "test.db")))


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_health(client):
    status, body, headers = client.request("GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}
    assert headers["Content-Type"] == "application/json"


def test_create_and_get(client):
    status, created, _ = client.request("POST", "/books", BOOK)
    assert status == 201
    assert created["id"] == 1
    assert {k: created[k] for k in BOOK} == BOOK

    status, fetched, _ = client.request("GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_minimal_book(client):
    status, created, _ = client.request("POST", "/books", {"title": "T", "author": "A"})
    assert status == 201
    assert created["year"] is None and created["isbn"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "A"},
        {"title": "T"},
        {"title": "", "author": "A"},
        {"title": "   ", "author": "A"},
        {"title": 5, "author": "A"},
        {"title": "T", "author": "A", "year": "1999"},
        {"title": "T", "author": "A", "year": True},
        {"title": "T", "author": "A", "isbn": 123},
        [],
    ],
)
def test_create_validation(client, payload):
    status, body, _ = client.request("POST", "/books", payload)
    assert status == 400
    assert "error" in body
    assert client.request("GET", "/books")[1] == []


def test_create_invalid_json(client):
    status, body, _ = client.request("POST", "/books", raw=b"{not json")
    assert status == 400
    status, body, _ = client.request("POST", "/books", raw=b"")
    assert status == 400


def test_list_and_author_filter(client):
    client.request("POST", "/books", BOOK)
    client.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    client.request("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    status, books, _ = client.request("GET", "/books")
    assert status == 200 and len(books) == 3

    status, books, _ = client.request("GET", "/books?author=Jane%20Austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma", "Persuasion"]

    status, books, _ = client.request("GET", "/books?author=Nobody")
    assert status == 200 and books == []


def test_update(client):
    _, created, _ = client.request("POST", "/books", BOOK)
    update = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "1"}
    status, updated, _ = client.request("PUT", f"/books/{created['id']}", update)
    assert status == 200
    assert updated == {"id": created["id"], **update}
    assert client.request("GET", f"/books/{created['id']}")[1] == updated


def test_update_validation_and_missing(client):
    _, created, _ = client.request("POST", "/books", BOOK)
    status, _, _ = client.request("PUT", f"/books/{created['id']}", {"title": "", "author": "A"})
    assert status == 400
    status, _, _ = client.request("PUT", "/books/999", {"title": "T", "author": "A"})
    assert status == 404


def test_delete(client):
    _, created, _ = client.request("POST", "/books", BOOK)
    status, body, _ = client.request("DELETE", f"/books/{created['id']}")
    assert status == 204 and body is None
    assert client.request("GET", f"/books/{created['id']}")[0] == 404
    assert client.request("DELETE", f"/books/{created['id']}")[0] == 404


def test_not_found_and_method_not_allowed(client):
    assert client.request("GET", "/books/42")[0] == 404
    assert client.request("GET", "/books/abc")[0] == 404
    assert client.request("GET", "/nope")[0] == 404
    assert client.request("PATCH", "/books")[0] == 405
    assert client.request("POST", "/health")[0] == 405


def test_persistence_across_app_instances(tmp_path):
    db = str(tmp_path / "p.db")
    Client(create_app(db)).request("POST", "/books", BOOK)
    status, books, _ = Client(create_app(db)).request("GET", "/books")
    assert status == 200 and len(books) == 1
