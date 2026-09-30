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
        env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": qs,
               "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)}
        out = {}
        chunks = self.app(env, lambda s, h: out.update(status=int(s.split()[0])))
        raw_out = b"".join(chunks)
        return out["status"], (json.loads(raw_out) if raw_out else None)


@pytest.fixture
def client(tmp_path):
    return Client(create_app(str(tmp_path / "t.db")))


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(client):
    assert client.request("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(client):
    status, book = client.request("POST", "/books", BOOK)
    assert status == 201 and book["id"] == 1 and book["title"] == "Dune"
    assert client.request("GET", f"/books/{book['id']}") == (200, book)


def test_validation(client):
    assert client.request("POST", "/books", {"author": "x"})[0] == 400
    assert client.request("POST", "/books", {"title": "  ", "author": "x"})[0] == 400
    assert client.request("POST", "/books", {"title": "t", "author": "a", "year": "1999"})[0] == 400
    assert client.request("POST", "/books", raw=b"{bad")[0] == 400
    assert client.request("POST", "/books", [1])[0] == 400


def test_list_and_author_filter(client):
    client.request("POST", "/books", BOOK)
    client.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(client.request("GET", "/books")[1]) == 2
    status, books = client.request("GET", "/books?author=Jane%20Austen")
    assert status == 200 and [b["title"] for b in books] == ["Emma"]
    assert client.request("GET", "/books?author=Nobody")[1] == []


def test_update(client):
    client.request("POST", "/books", BOOK)
    status, book = client.request("PUT", "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert status == 200 and book["title"] == "Dune Messiah"
    assert client.request("PUT", "/books/1", {"title": "x"})[0] == 400
    assert client.request("PUT", "/books/99", BOOK)[0] == 404


def test_delete(client):
    client.request("POST", "/books", BOOK)
    assert client.request("DELETE", "/books/1") == (204, None)
    assert client.request("GET", "/books/1")[0] == 404
    assert client.request("DELETE", "/books/1")[0] == 404


def test_unknown_route_and_method(client):
    assert client.request("GET", "/nope")[0] == 404
    assert client.request("PATCH", "/books")[0] == 405
