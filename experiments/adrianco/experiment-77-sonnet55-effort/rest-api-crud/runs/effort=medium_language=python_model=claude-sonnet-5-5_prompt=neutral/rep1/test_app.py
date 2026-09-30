import json
import threading
import urllib.error
import urllib.request

import pytest

from app import make_server


@pytest.fixture()
def base():
    server = make_server(":memory:", port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "111"}


def test_health(base):
    assert call(base, "GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(base):
    status, book = call(base, "POST", "/books", BOOK)
    assert status == 201
    assert book["id"] == 1 and book["title"] == "Dune"
    assert call(base, "GET", f"/books/{book['id']}") == (200, book)


def test_validation(base):
    assert call(base, "POST", "/books", {"author": "x"})[0] == 400
    assert call(base, "POST", "/books", {"title": "x", "author": "  "})[0] == 400
    assert call(base, "POST", "/books", {**BOOK, "year": "1965"})[0] == 400
    assert call(base, "PUT", "/books/1", {"title": "x"})[0] == 400


def test_invalid_json(base):
    req = urllib.request.Request(base + "/books", data=b"{bad", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 400


def test_list_and_author_filter(base):
    call(base, "POST", "/books", BOOK)
    call(base, "POST", "/books", {**BOOK, "title": "Emma", "author": "Jane Austen"})
    assert len(call(base, "GET", "/books")[1]) == 2
    status, books = call(base, "GET", "/books?author=Jane%20Austen")
    assert status == 200 and [b["title"] for b in books] == ["Emma"]
    assert call(base, "GET", "/books?author=nobody")[1] == []


def test_update(base):
    call(base, "POST", "/books", BOOK)
    status, book = call(base, "PUT", "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert status == 200 and book["title"] == "Dune Messiah"
    assert call(base, "GET", "/books/1")[1]["title"] == "Dune Messiah"
    assert call(base, "PUT", "/books/99", BOOK)[0] == 404


def test_delete(base):
    call(base, "POST", "/books", BOOK)
    assert call(base, "DELETE", "/books/1")[0] == 204
    assert call(base, "GET", "/books/1")[0] == 404
    assert call(base, "DELETE", "/books/1")[0] == 404


def test_unknown_route(base):
    assert call(base, "GET", "/nope")[0] == 404
