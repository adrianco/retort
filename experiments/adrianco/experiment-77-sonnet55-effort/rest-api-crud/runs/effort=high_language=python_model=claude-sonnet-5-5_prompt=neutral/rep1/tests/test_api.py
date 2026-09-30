import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


class Client:
    """Minimal WSGI test client."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, body=None, raw=None):
        path, _, query = path.partition("?")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(data)),
            "wsgi.input": io.BytesIO(data),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        out = b"".join(self.app(environ, start_response))
        parsed = json.loads(out) if out else None
        return captured["status"], parsed, captured["headers"]


@pytest.fixture
def client(tmp_path):
    return Client(create_app(str(tmp_path / "test.db")))


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_health(client):
    status, body, _ = client.request("GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_create_and_get_book(client):
    status, created, headers = client.request("POST", "/books", BOOK)
    assert status == 201
    assert created["id"] == 1
    assert {k: created[k] for k in BOOK} == BOOK
    assert headers["Location"] == "/books/1"

    status, fetched, _ = client.request("GET", "/books/1")
    assert status == 200
    assert fetched == created


def test_create_requires_title_and_author(client):
    status, body, _ = client.request("POST", "/books", {"year": 2000})
    assert status == 400
    assert set(body["details"]) == {"title", "author"}

    status, _, _ = client.request("POST", "/books", {"title": "  ", "author": "X"})
    assert status == 400
    assert client.request("GET", "/books")[1] == []


def test_create_rejects_bad_types_and_json(client):
    assert client.request("POST", "/books", {"title": "T", "author": "A", "year": "1999"})[0] == 400
    assert client.request("POST", "/books", {"title": "T", "author": "A", "year": True})[0] == 400
    assert client.request("POST", "/books", {"title": "T", "author": "A", "isbn": 123})[0] == 400
    assert client.request("POST", "/books", raw=b"{not json")[0] == 400
    assert client.request("POST", "/books", ["a list"])[0] == 400


def test_optional_fields(client):
    status, created, _ = client.request("POST", "/books", {"title": "T", "author": "A"})
    assert status == 201
    assert created["year"] is None and created["isbn"] is None


def test_list_and_author_filter(client):
    client.request("POST", "/books", BOOK)
    client.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    client.request("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    assert len(client.request("GET", "/books")[1]) == 3
    status, books, _ = client.request("GET", "/books?author=Jane%20Austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma", "Persuasion"]
    assert client.request("GET", "/books?author=Nobody")[1] == []


def test_update_book(client):
    client.request("POST", "/books", BOOK)
    updated = dict(BOOK, title="Dune Messiah", year=1969)
    status, body, _ = client.request("PUT", "/books/1", updated)
    assert status == 200
    assert body["title"] == "Dune Messiah" and body["year"] == 1969
    assert client.request("GET", "/books/1")[1] == body


def test_update_validation_and_missing(client):
    client.request("POST", "/books", BOOK)
    assert client.request("PUT", "/books/1", {"title": "", "author": "A"})[0] == 400
    assert client.request("GET", "/books/1")[1]["title"] == "Dune"
    assert client.request("PUT", "/books/99", BOOK)[0] == 404


def test_delete_book(client):
    client.request("POST", "/books", BOOK)
    status, body, _ = client.request("DELETE", "/books/1")
    assert status == 204 and body is None
    assert client.request("GET", "/books/1")[0] == 404
    assert client.request("DELETE", "/books/1")[0] == 404


def test_not_found_and_method_not_allowed(client):
    assert client.request("GET", "/books/42")[0] == 404
    assert client.request("GET", "/books/abc")[0] == 404
    assert client.request("GET", "/nope")[0] == 404
    status, _, headers = client.request("PATCH", "/books/1")
    assert status == 405 and "GET" in headers["Allow"]
    assert client.request("POST", "/health")[0] == 405


def test_data_persists_across_app_instances(tmp_path):
    db = str(tmp_path / "persist.db")
    Client(create_app(db)).request("POST", "/books", BOOK)
    status, books, _ = Client(create_app(db)).request("GET", "/books")
    assert status == 200 and len(books) == 1


def test_in_memory_database():
    client = Client(create_app(":memory:"))
    client.request("POST", "/books", BOOK)
    assert len(client.request("GET", "/books")[1]) == 1
