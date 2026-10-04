import json
import threading
import urllib.error
import urllib.request

import pytest

from app import create_server, validate_book, ValidationError


@pytest.fixture
def api(tmp_path):
    server = create_server(port=0, db_path=str(tmp_path / "test.db"), quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def request(method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status, payload = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, payload = exc.code, exc.read()
        return status, json.loads(payload) if payload else None

    yield request
    server.shutdown()
    server.server_close()
    server.store.close()
    thread.join(timeout=5)


DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_health(api):
    assert api("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get_book(api):
    status, created = api("POST", "/books", DUNE)
    assert status == 201
    assert created == {"id": created["id"], **DUNE}

    status, fetched = api("GET", f"/books/{created['id']}")
    assert status == 200
    assert fetched == created


def test_create_with_only_required_fields(api):
    status, created = api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    assert status == 201
    assert created["year"] is None and created["isbn"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"author": "Frank Herbert"},
        {"title": "Dune"},
        {"title": "   ", "author": "Frank Herbert"},
        {"title": "Dune", "author": 42},
        {"title": "Dune", "author": "Frank Herbert", "year": "1965"},
        {"title": "Dune", "author": "Frank Herbert", "isbn": 123},
        ["not", "an", "object"],
        None,
    ],
)
def test_create_rejects_invalid_body(api, body):
    raw = b"null" if body is None else None
    status, payload = api("POST", "/books", body, raw=raw)
    assert status == 400
    assert payload["error"] == "validation failed"
    assert payload["details"]
    assert api("GET", "/books") == (200, [])


def test_create_rejects_malformed_json(api):
    status, payload = api("POST", "/books", raw=b"{not json")
    assert status == 400
    assert "JSON" in payload["error"]


def test_list_books_and_author_filter(api):
    api("POST", "/books", DUNE)
    api("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    api("POST", "/books", {"title": "Dune Messiah", "author": "Frank Herbert"})

    status, books = api("GET", "/books")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Emma", "Dune Messiah"]

    status, books = api("GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in books] == ["Dune", "Dune Messiah"]

    assert api("GET", "/books?author=Nobody") == (200, [])


def test_update_book(api):
    _, created = api("POST", "/books", DUNE)
    update = {"title": "Dune (Revised)", "author": "Frank Herbert", "year": 1966}

    status, updated = api("PUT", f"/books/{created['id']}", update)
    assert status == 200
    assert updated == {"id": created["id"], **update, "isbn": None}
    assert api("GET", f"/books/{created['id']}") == (200, updated)


def test_update_validates_and_handles_missing(api):
    _, created = api("POST", "/books", DUNE)
    status, _ = api("PUT", f"/books/{created['id']}", {"title": "No author"})
    assert status == 400
    assert api("GET", f"/books/{created['id']}")[1] == created

    assert api("PUT", "/books/9999", DUNE)[0] == 404


def test_delete_book(api):
    _, created = api("POST", "/books", DUNE)
    assert api("DELETE", f"/books/{created['id']}") == (204, None)
    assert api("GET", f"/books/{created['id']}")[0] == 404
    assert api("DELETE", f"/books/{created['id']}")[0] == 404


def test_unknown_routes_and_methods(api):
    assert api("GET", "/books/9999")[0] == 404
    assert api("GET", "/books/abc")[0] == 404
    assert api("GET", "/nope")[0] == 404
    assert api("DELETE", "/books")[0] == 405
    assert api("POST", "/health", {})[0] == 405


def test_data_persists_across_restarts(tmp_path):
    from app import BookStore

    path = str(tmp_path / "persist.db")
    store = BookStore(path)
    created = store.create(validate_book(DUNE))
    store.close()

    reopened = BookStore(path)
    assert reopened.get(created["id"]) == created
    reopened.close()


def test_validate_book_strips_whitespace():
    assert validate_book({"title": " Dune ", "author": " Frank Herbert "}) == {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": None,
        "isbn": None,
    }
    with pytest.raises(ValidationError):
        validate_book({"title": "Dune", "author": "Frank Herbert", "year": True})
