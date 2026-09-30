import json
import threading
import urllib.error
import urllib.request

import pytest

from app import make_server


@pytest.fixture()
def base():
    server = make_server(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def call(base, method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            text = r.read()
            return r.status, json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        text = e.read()
        return e.code, json.loads(text) if text else None


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(base):
    assert call(base, "GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(base):
    status, created = call(base, "POST", "/books", BOOK)
    assert status == 201 and created["id"] == 1 and created["title"] == "Dune"
    assert call(base, "GET", "/books/1") == (200, created)


def test_validation(base):
    assert call(base, "POST", "/books", {"author": "x"})[0] == 422
    assert call(base, "POST", "/books", {"title": "  ", "author": "x"})[0] == 422
    assert call(base, "POST", "/books", {"title": "t", "author": "a", "year": "1999"})[0] == 422
    assert call(base, "POST", "/books", raw=b"{bad")[0] == 400
    assert call(base, "POST", "/books", [1])[0] == 422


def test_list_and_author_filter(base):
    call(base, "POST", "/books", BOOK)
    call(base, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(call(base, "GET", "/books")[1]) == 2
    status, books = call(base, "GET", "/books?author=Jane%20Austen")
    assert status == 200 and [b["title"] for b in books] == ["Emma"]
    assert call(base, "GET", "/books?author=nobody")[1] == []


def test_update(base):
    call(base, "POST", "/books", BOOK)
    status, updated = call(base, "PUT", "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert status == 200 and updated["title"] == "Dune Messiah"
    assert call(base, "PUT", "/books/1", {"title": "x"})[0] == 422
    assert call(base, "PUT", "/books/99", BOOK)[0] == 404


def test_delete(base):
    call(base, "POST", "/books", BOOK)
    assert call(base, "DELETE", "/books/1") == (204, None)
    assert call(base, "GET", "/books/1")[0] == 404
    assert call(base, "DELETE", "/books/1")[0] == 404


def test_unknown_route(base):
    assert call(base, "GET", "/nope")[0] == 404
