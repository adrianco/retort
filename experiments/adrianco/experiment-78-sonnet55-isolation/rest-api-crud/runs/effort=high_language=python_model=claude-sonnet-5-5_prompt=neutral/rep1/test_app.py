import io
import json

import pytest

from app import create_app


class Client:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, body=None, raw=None):
        path, _, qs = path.partition("?")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": qs,
            "CONTENT_LENGTH": str(len(data)),
            "wsgi.input": io.BytesIO(data),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        out = b"".join(self.app(environ, start_response))
        return captured["status"], (json.loads(out) if out else None), captured["headers"]


@pytest.fixture
def client(tmp_path):
    return Client(create_app(str(tmp_path / "test.db")))


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(client):
    status, body, headers = client.request("GET", "/health")
    assert status == 200 and body == {"status": "ok"}
    assert headers["Content-Type"] == "application/json"


def test_create_and_get(client):
    status, body, _ = client.request("POST", "/books", BOOK)
    assert status == 201
    assert body == {"id": 1, **BOOK}
    status, body, _ = client.request("GET", "/books/1")
    assert status == 200 and body["title"] == "Dune"


@pytest.mark.parametrize("payload", [
    {"author": "A"},
    {"title": "T"},
    {"title": "  ", "author": "A"},
    {"title": "T", "author": 5},
    {"title": "T", "author": "A", "year": "1999"},
    {"title": "T", "author": "A", "year": True},
    {"title": "T", "author": "A", "isbn": 123},
])
def test_create_validation(client, payload):
    status, body, _ = client.request("POST", "/books", payload)
    assert status == 422 and "error" in body
    assert client.request("GET", "/books")[1] == []


def test_invalid_json(client):
    assert client.request("POST", "/books", raw=b"{nope")[0] == 400
    assert client.request("POST", "/books", raw=b"[1]")[0] == 400


def test_list_and_author_filter(client):
    client.request("POST", "/books", BOOK)
    client.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    client.request("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})
    assert len(client.request("GET", "/books")[1]) == 3
    status, body, _ = client.request("GET", "/books?author=Jane%20Austen")
    assert status == 200 and [b["title"] for b in body] == ["Emma", "Persuasion"]
    assert client.request("GET", "/books?author=Nobody")[1] == []


def test_update(client):
    client.request("POST", "/books", BOOK)
    status, body, _ = client.request("PUT", "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert status == 200 and body["title"] == "Dune Messiah"
    assert client.request("GET", "/books/1")[1]["title"] == "Dune Messiah"
    assert client.request("PUT", "/books/1", {"author": "x"})[0] == 422
    assert client.request("PUT", "/books/99", BOOK)[0] == 404


def test_delete(client):
    client.request("POST", "/books", BOOK)
    assert client.request("DELETE", "/books/1")[0] == 200
    assert client.request("GET", "/books/1")[0] == 404
    assert client.request("DELETE", "/books/1")[0] == 404


def test_not_found_and_method_errors(client):
    assert client.request("GET", "/books/abc")[0] == 404
    assert client.request("GET", "/books/999")[0] == 404
    assert client.request("GET", "/nope")[0] == 404
    assert client.request("PATCH", "/books/1")[0] == 405
    assert client.request("POST", "/health")[0] == 405
