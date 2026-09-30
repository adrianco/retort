import json
import threading
import urllib.error
import urllib.request

import pytest

from app import create_server


@pytest.fixture()
def base(tmp_path):
    server = create_server(port=0, db_path=str(tmp_path / "t.db"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def call(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}


def test_health(base):
    assert call(base, "GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(base):
    s, b = call(base, "POST", "/books", BOOK)
    assert s == 201 and b["id"] == 1
    assert call(base, "GET", "/books/1") == (200, b)


def test_validation(base):
    assert call(base, "POST", "/books", {"author": "x"})[0] == 400
    assert call(base, "POST", "/books", {"title": " ", "author": "x"})[0] == 400
    assert call(base, "POST", "/books", {**BOOK, "year": "1965"})[0] == 400


def test_list_and_filter(base):
    call(base, "POST", "/books", BOOK)
    call(base, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(call(base, "GET", "/books")[1]) == 2
    s, b = call(base, "GET", "/books?author=Jane%20Austen")
    assert s == 200 and [x["title"] for x in b] == ["Emma"]


def test_update(base):
    call(base, "POST", "/books", BOOK)
    s, b = call(base, "PUT", "/books/1", {**BOOK, "title": "Dune 2"})
    assert s == 200 and b["title"] == "Dune 2"
    assert call(base, "GET", "/books/1")[1]["title"] == "Dune 2"
    assert call(base, "PUT", "/books/9", BOOK)[0] == 404
    assert call(base, "PUT", "/books/1", {"title": "x"})[0] == 400


def test_delete(base):
    call(base, "POST", "/books", BOOK)
    assert call(base, "DELETE", "/books/1")[0] == 204
    assert call(base, "GET", "/books/1")[0] == 404
    assert call(base, "DELETE", "/books/1")[0] == 404
