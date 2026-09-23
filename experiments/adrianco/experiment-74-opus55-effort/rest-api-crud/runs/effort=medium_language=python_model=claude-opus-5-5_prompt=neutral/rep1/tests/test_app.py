import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import ValidationError, create_server, validate_book  # noqa: E402


@pytest.fixture
def base_url(tmp_path):
    server = create_server(port=0, db_path=str(tmp_path / "test.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    server.store.close()


def request(method, url, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            return resp.status, json.loads(content) if content else None
    except urllib.error.HTTPError as e:
        content = e.read()
        return e.code, json.loads(content) if content else None


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


def test_health(base_url):
    assert request("GET", f"{base_url}/health") == (200, {"status": "ok"})


def test_create_and_get(base_url):
    status, created = request("POST", f"{base_url}/books", BOOK)
    assert status == 201
    assert created["id"] > 0
    assert {k: created[k] for k in BOOK} == BOOK

    status, fetched = request("GET", f"{base_url}/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_requires_title_and_author(base_url):
    status, body = request("POST", f"{base_url}/books", {"year": 2000})
    assert status == 400
    assert set(body["details"]) == {"title", "author"}

    status, body = request("POST", f"{base_url}/books", {"title": "  ", "author": "X"})
    assert status == 400
    assert "title" in body["details"]


def test_create_rejects_invalid_json(base_url):
    status, body = request("POST", f"{base_url}/books", raw=b"{not json")
    assert status == 400
    assert body["details"]["body"] == "invalid JSON"


def test_list_and_author_filter(base_url):
    request("POST", f"{base_url}/books", BOOK)
    request("POST", f"{base_url}/books", {"title": "Emma", "author": "Jane Austen"})
    request("POST", f"{base_url}/books", {"title": "Persuasion", "author": "Jane Austen"})

    status, books = request("GET", f"{base_url}/books")
    assert status == 200
    assert len(books) == 3

    status, books = request("GET", f"{base_url}/books?author=Jane%20Austen")
    assert status == 200
    assert [b["title"] for b in books] == ["Emma", "Persuasion"]

    _, books = request("GET", f"{base_url}/books?author=nobody")
    assert books == []


def test_update(base_url):
    _, created = request("POST", f"{base_url}/books", BOOK)
    url = f"{base_url}/books/{created['id']}"
    status, updated = request("PUT", url, {**BOOK, "title": "Dune Messiah", "year": 1969})
    assert status == 200
    assert updated["title"] == "Dune Messiah" and updated["year"] == 1969
    assert request("GET", url)[1] == updated

    status, _ = request("PUT", url, {"title": "No author"})
    assert status == 400

    status, _ = request("PUT", f"{base_url}/books/9999", BOOK)
    assert status == 404


def test_delete(base_url):
    _, created = request("POST", f"{base_url}/books", BOOK)
    url = f"{base_url}/books/{created['id']}"
    assert request("DELETE", url) == (204, None)
    assert request("GET", url)[0] == 404
    assert request("DELETE", url)[0] == 404


def test_unknown_routes_return_404(base_url):
    assert request("GET", f"{base_url}/nope")[0] == 404
    assert request("GET", f"{base_url}/books/abc")[0] == 404


def test_persistence_across_restarts(tmp_path):
    db = str(tmp_path / "persist.db")
    for expected in (1, 2):
        server = create_server(port=0, db_path=db)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        url = f"http://127.0.0.1:{server.server_address[1]}/books"
        request("POST", url, BOOK)
        assert len(request("GET", url)[1]) == expected
        server.shutdown()
        server.server_close()
        server.store.close()


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "isbn": "123"}, "isbn"),
        ({"title": 5, "author": "A"}, "title"),
    ],
)
def test_validate_book_rejects_bad_fields(payload, field):
    with pytest.raises(ValidationError) as exc:
        validate_book(payload)
    assert field in exc.value.errors


def test_validate_book_rejects_non_object():
    with pytest.raises(ValidationError):
        validate_book([1, 2])
