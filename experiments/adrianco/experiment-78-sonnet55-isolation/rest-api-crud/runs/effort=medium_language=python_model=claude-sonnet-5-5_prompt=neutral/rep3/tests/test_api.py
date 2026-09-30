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

    def call(self, method, path, body=None):
        raw = json.dumps(body).encode() if body is not None else b""
        path, _, qs = path.partition("?")
        env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": qs,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        out = {}
        res = self.app(env, lambda s, h: out.setdefault("status", int(s.split()[0])))
        data = b"".join(res)
        return out["status"], (json.loads(data) if data else None)


@pytest.fixture
def client(tmp_path):
    return Client(create_app(str(tmp_path / "t.db")))


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}


def test_health(client):
    assert client.call("GET", "/health") == (200, {"status": "ok"})


def test_crud_lifecycle(client):
    s, b = client.call("POST", "/books", BOOK)
    assert s == 201 and b["id"] == 1
    assert client.call("GET", "/books/1") == (200, b)
    s, u = client.call("PUT", "/books/1", {**BOOK, "title": "Dune 2"})
    assert s == 200 and u["title"] == "Dune 2"
    assert client.call("DELETE", "/books/1") == (204, None)
    assert client.call("GET", "/books/1")[0] == 404


def test_list_and_author_filter(client):
    client.call("POST", "/books", BOOK)
    client.call("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(client.call("GET", "/books")[1]) == 2
    s, r = client.call("GET", "/books?author=Jane%20Austen")
    assert s == 200 and [x["title"] for x in r] == ["Emma"]


@pytest.mark.parametrize("bad", [{}, {"title": "x"}, {"author": "x"},
                                 {"title": " ", "author": "x"},
                                 {"title": "x", "author": "y", "year": "1999"}])
def test_validation(client, bad):
    assert client.call("POST", "/books", bad)[0] == 400
    client.call("POST", "/books", BOOK)
    assert client.call("PUT", "/books/1", bad)[0] == 400


def test_missing_and_invalid(client):
    assert client.call("PUT", "/books/99", BOOK)[0] == 404
    assert client.call("DELETE", "/books/99")[0] == 404
    assert client.call("GET", "/nope")[0] == 404
