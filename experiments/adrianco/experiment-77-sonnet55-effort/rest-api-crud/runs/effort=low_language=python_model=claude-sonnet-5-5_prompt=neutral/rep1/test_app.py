import json
import threading
import urllib.error
import urllib.request

import pytest

from app import create_server


@pytest.fixture()
def base():
    srv = create_server(port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(method, url, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            text = r.read()
            return r.status, json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}


def test_health(base):
    assert call("GET", base + "/health") == (200, {"status": "ok"})


def test_crud_lifecycle(base):
    s, b = call("POST", base + "/books", BOOK)
    assert s == 201 and b["id"] == 1 and b["title"] == "Dune"
    assert call("GET", base + "/books/1")[1]["author"] == "Frank Herbert"
    s, b = call("PUT", base + "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert s == 200 and b["title"] == "Dune Messiah"
    assert call("DELETE", base + "/books/1") == (204, None)
    assert call("GET", base + "/books/1")[0] == 404


def test_list_and_author_filter(base):
    call("POST", base + "/books", BOOK)
    call("POST", base + "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(call("GET", base + "/books")[1]) == 2
    res = call("GET", base + "/books?author=Jane%20Austen")[1]
    assert [x["title"] for x in res] == ["Emma"]


@pytest.mark.parametrize("payload", [
    {"author": "A"}, {"title": "T"}, {"title": " ", "author": "A"},
    {"title": "T", "author": "A", "year": "x"},
])
def test_validation(base, payload):
    assert call("POST", base + "/books", payload)[0] == 400
    assert call("PUT", base + "/books/1", payload)[0] in (400,)


def test_invalid_json_and_missing(base):
    assert call("POST", base + "/books", raw=b"{bad")[0] == 400
    assert call("PUT", base + "/books/99", BOOK)[0] == 404
    assert call("DELETE", base + "/books/99")[0] == 404
