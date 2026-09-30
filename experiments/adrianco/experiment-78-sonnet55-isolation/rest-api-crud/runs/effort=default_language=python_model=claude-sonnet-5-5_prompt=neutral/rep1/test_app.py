import http.client
import json
import threading

import pytest

from app import create_server


@pytest.fixture()
def call():
    server = create_server(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def _call(method, path, body=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", port)
        data = raw if raw is not None else (json.dumps(body) if body is not None else None)
        conn.request(method, path, body=data)
        r = conn.getresponse()
        text = r.read()
        conn.close()
        return r.status, (json.loads(text) if text else None)

    yield _call
    server.shutdown()
    server.server_close()


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}


def test_health(call):
    assert call("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(call):
    status, b = call("POST", "/books", BOOK)
    assert status == 201 and b["id"] == 1 and b["title"] == "Dune"
    assert call("GET", "/books/1") == (200, b)


def test_validation(call):
    assert call("POST", "/books", {"author": "x"})[0] == 400
    assert call("POST", "/books", {"title": "  ", "author": "x"})[0] == 400
    assert call("POST", "/books", {"title": "t", "author": "a", "year": "1"})[0] == 400
    assert call("POST", "/books", raw="{bad")[0] == 400


def test_list_and_filter(call):
    call("POST", "/books", BOOK)
    call("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert len(call("GET", "/books")[1]) == 2
    res = call("GET", "/books?author=Jane%20Austen")[1]
    assert [b["title"] for b in res] == ["Emma"]


def test_update(call):
    call("POST", "/books", BOOK)
    status, b = call("PUT", "/books/1", {**BOOK, "title": "Dune Messiah"})
    assert status == 200 and b["title"] == "Dune Messiah"
    assert call("PUT", "/books/1", {"title": "x"})[0] == 400
    assert call("PUT", "/books/99", BOOK)[0] == 404


def test_delete_and_404(call):
    call("POST", "/books", BOOK)
    assert call("DELETE", "/books/1")[0] == 204
    assert call("GET", "/books/1")[0] == 404
    assert call("DELETE", "/books/1")[0] == 404
