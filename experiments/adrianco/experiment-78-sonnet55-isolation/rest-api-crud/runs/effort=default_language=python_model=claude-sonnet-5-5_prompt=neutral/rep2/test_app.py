import io
import json

import pytest

from app import App


@pytest.fixture
def client(tmp_path):
    app = App(str(tmp_path / "t.db"))

    def call(method, path, body=None, query=""):
        raw = json.dumps(body).encode() if body is not None else b""
        env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        out = {}
        res = app(env, lambda s, h: out.update(status=int(s.split()[0])))
        return out["status"], json.loads(b"".join(res))
    return call


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}


def test_health(client):
    assert client("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(client):
    s, b = client("POST", "/books", BOOK)
    assert s == 201 and b["id"] == 1 and b["title"] == "Dune"
    assert client("GET", "/books/1") == (200, b)


def test_validation(client):
    s, _ = client("POST", "/books", {"author": "x"})
    assert s == 400
    assert client("POST", "/books", {"title": "  ", "author": "x"})[0] == 400
    assert client("POST", "/books", {**BOOK, "year": "1965"})[0] == 400


def test_list_and_filter(client):
    client("POST", "/books", BOOK)
    client("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(client("GET", "/books")[1]) == 2
    s, b = client("GET", "/books", query="author=Jane+Austen")
    assert s == 200 and [x["title"] for x in b] == ["Emma"]


def test_update(client):
    client("POST", "/books", BOOK)
    s, b = client("PUT", "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert s == 200 and b["title"] == "Dune Messiah"
    assert client("PUT", "/books/1", {"title": "x"})[0] == 400
    assert client("PUT", "/books/9", BOOK)[0] == 404


def test_delete(client):
    client("POST", "/books", BOOK)
    assert client("DELETE", "/books/1")[0] == 200
    assert client("GET", "/books/1")[0] == 404
    assert client("DELETE", "/books/1")[0] == 404


def test_not_found_and_bad_json(client):
    assert client("GET", "/nope")[0] == 404
    env = {"REQUEST_METHOD": "POST", "PATH_INFO": "/books", "QUERY_STRING": "",
           "CONTENT_LENGTH": "3", "wsgi.input": io.BytesIO(b"{no")}
    out = {}
    App(":memory:")(env, lambda s, h: out.update(s=s))
    assert out["s"].startswith("400")
