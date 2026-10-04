import json
import threading
import urllib.error
import urllib.request

import pytest

from app import make_server


@pytest.fixture
def api(tmp_path):
    server = make_server(port=0, db_path=str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def call(method, path, body=None, raw=None):
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None
        )
        req = urllib.request.Request(base + path, data=data, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
                status = resp.status
        except urllib.error.HTTPError as exc:
            content = exc.read()
            status = exc.code
        return status, (json.loads(content) if content else None)

    yield call
    server.shutdown()
    server.server_close()
    server.RequestHandlerClass.store.close()


DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_health(api):
    assert api("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get(api):
    status, book = api("POST", "/books", DUNE)
    assert status == 201
    assert book == {"id": book["id"], **DUNE}
    assert api("GET", f"/books/{book['id']}") == (200, book)


def test_create_minimal(api):
    status, book = api("POST", "/books", {"title": "T", "author": "A"})
    assert status == 201
    assert book["year"] is None and book["isbn"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "A"},
        {"title": "T"},
        {"title": "  ", "author": "A"},
        {"title": "T", "author": "A", "year": "1999"},
        {"title": "T", "author": "A", "isbn": 123},
        ["not", "an", "object"],
    ],
)
def test_create_validation(api, payload):
    status, body = api("POST", "/books", payload)
    assert status == 400
    assert "error" in body


def test_create_invalid_json(api):
    status, body = api("POST", "/books", raw=b"{nope")
    assert status == 400
    assert "error" in body


def test_list_and_author_filter(api):
    api("POST", "/books", DUNE)
    api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    status, books = api("GET", "/books")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Emma"]
    status, books = api("GET", "/books?author=Jane%20Austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma"]
    assert api("GET", "/books?author=Nobody") == (200, [])


def test_update(api):
    _, book = api("POST", "/books", DUNE)
    updated = {**DUNE, "title": "Dune Messiah", "year": 1969}
    status, body = api("PUT", f"/books/{book['id']}", updated)
    assert status == 200
    assert body == {"id": book["id"], **updated}
    assert api("GET", f"/books/{book['id']}")[1]["title"] == "Dune Messiah"


def test_update_validation_and_missing(api):
    _, book = api("POST", "/books", DUNE)
    assert api("PUT", f"/books/{book['id']}", {"title": "x"})[0] == 400
    assert api("PUT", "/books/9999", DUNE)[0] == 404


def test_delete(api):
    _, book = api("POST", "/books", DUNE)
    assert api("DELETE", f"/books/{book['id']}") == (204, None)
    assert api("GET", f"/books/{book['id']}")[0] == 404
    assert api("DELETE", f"/books/{book['id']}")[0] == 404


def test_not_found_and_method_not_allowed(api):
    assert api("GET", "/books/9999")[0] == 404
    assert api("GET", "/nope")[0] == 404
    assert api("GET", "/books/abc")[0] == 404
    assert api("DELETE", "/books")[0] == 405
