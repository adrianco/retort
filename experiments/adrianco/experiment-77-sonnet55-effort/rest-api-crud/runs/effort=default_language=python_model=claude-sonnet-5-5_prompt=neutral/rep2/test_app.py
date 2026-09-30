import json
import threading
import urllib.error
import urllib.request

import pytest

from app import create_server


@pytest.fixture()
def base():
    srv = create_server(port=0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(method, url, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            payload = r.read()
            return r.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as e:
        payload = e.read()
        return e.code, json.loads(payload) if payload else None


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "111"}


def test_health(base):
    assert call("GET", base + "/health") == (200, {"status": "ok"})


def test_create_and_get(base):
    status, book = call("POST", base + "/books", BOOK)
    assert status == 201 and book["id"] == 1 and book["title"] == "Dune"
    assert call("GET", base + "/books/1") == (200, book)


def test_validation(base):
    assert call("POST", base + "/books", {"author": "x"})[0] == 400
    assert call("POST", base + "/books", {"title": "  ", "author": "x"})[0] == 400
    assert call("POST", base + "/books", {**BOOK, "year": "1965"})[0] == 400
    assert call("POST", base + "/books", raw=b"{bad")[0] == 400
    assert call("PUT", base + "/books/1", {"title": "t"})[0] == 400


def test_list_and_author_filter(base):
    call("POST", base + "/books", BOOK)
    call("POST", base + "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(call("GET", base + "/books")[1]) == 2
    got = call("GET", base + "/books?author=Jane%20Austen")[1]
    assert [b["title"] for b in got] == ["Emma"]


def test_update(base):
    call("POST", base + "/books", BOOK)
    status, book = call("PUT", base + "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert status == 200 and book["title"] == "Dune Messiah"
    assert call("PUT", base + "/books/99", BOOK)[0] == 404


def test_delete(base):
    call("POST", base + "/books", BOOK)
    assert call("DELETE", base + "/books/1")[0] == 204
    assert call("GET", base + "/books/1")[0] == 404
    assert call("DELETE", base + "/books/1")[0] == 404


def test_unknown_route(base):
    assert call("GET", base + "/nope")[0] == 404
