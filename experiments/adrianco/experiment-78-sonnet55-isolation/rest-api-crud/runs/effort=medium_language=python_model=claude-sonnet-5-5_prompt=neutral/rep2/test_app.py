import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import make_server

import pytest

from app import create_app, _Quiet


@pytest.fixture
def base(tmp_path):
    srv = make_server("127.0.0.1", 0, create_app(str(tmp_path / "t.db")), handler_class=_Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()


def call(base, method, path, body=None, raw=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    req = urllib.request.Request(base + path, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read()
            return r.status, json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(base):
    assert call(base, "GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(base):
    s, b = call(base, "POST", "/books", BOOK)
    assert s == 201 and b["id"] == 1 and b["title"] == "Dune"
    assert call(base, "GET", "/books/1") == (200, b)


def test_validation(base):
    assert call(base, "POST", "/books", {"author": "x"})[0] == 400
    assert call(base, "POST", "/books", {"title": " ", "author": "x"})[0] == 400
    assert call(base, "POST", "/books", {**BOOK, "year": "1965"})[0] == 400
    assert call(base, "POST", "/books", raw=b"{bad")[0] == 400
    assert call(base, "PUT", "/books/1", {"title": "t"})[0] == 400


def test_list_and_filter(base):
    call(base, "POST", "/books", BOOK)
    call(base, "POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(call(base, "GET", "/books")[1]) == 2
    res = call(base, "GET", "/books?author=Jane%20Austen")[1]
    assert [b["title"] for b in res] == ["Emma"]


def test_update_delete(base):
    call(base, "POST", "/books", BOOK)
    s, b = call(base, "PUT", "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert s == 200 and b["title"] == "Dune Messiah"
    assert call(base, "DELETE", "/books/1") == (204, None)
    assert call(base, "GET", "/books/1")[0] == 404


def test_not_found(base):
    assert call(base, "GET", "/books/99")[0] == 404
    assert call(base, "PUT", "/books/99", BOOK)[0] == 404
    assert call(base, "DELETE", "/books/99")[0] == 404
    assert call(base, "GET", "/nope")[0] == 404
