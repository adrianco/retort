import json
import threading
import urllib.error
import urllib.request

import pytest

from app import create_server


@pytest.fixture()
def base(tmp_path):
    srv = create_server(str(tmp_path / "t.db"), port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_health(base):
    assert call("GET", base + "/health") == (200, {"status": "ok"})


def test_crud_flow(base):
    s, b = call("POST", base + "/books", {"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "1"})
    assert s == 201 and b["id"]
    url = f"{base}/books/{b['id']}"
    assert call("GET", url)[1]["title"] == "Dune"
    s, b2 = call("PUT", url, {"title": "Dune 2", "author": "Herbert"})
    assert s == 200 and b2["title"] == "Dune 2"
    assert call("DELETE", url)[0] == 200
    assert call("GET", url)[0] == 404


def test_validation(base):
    assert call("POST", base + "/books", {"author": "x"})[0] == 400
    assert call("POST", base + "/books", {"title": "x", "author": " "})[0] == 400
    assert call("POST", base + "/books", {"title": "x", "author": "y", "year": "z"})[0] == 400


def test_author_filter(base):
    call("POST", base + "/books", {"title": "A", "author": "X"})
    call("POST", base + "/books", {"title": "B", "author": "Y"})
    s, books = call("GET", base + "/books?author=X")
    assert s == 200 and [b["title"] for b in books] == ["A"]
    assert len(call("GET", base + "/books")[1]) == 2


def test_missing(base):
    assert call("PUT", base + "/books/99", {"title": "a", "author": "b"})[0] == 404
    assert call("DELETE", base + "/books/99")[0] == 404
